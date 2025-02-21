import requests

class ServiceMonitor:
    def __init__(self, kibana_url='', headers={}, error_keywords=[], service_down_threshold=5, log_message=None, send_mail=None, send_via_hook=None, send_slack=None, slack_channel='', service_output_file='services.log'):
        self.KIBANA_URL = kibana_url
        self.Headers = headers
        self.ERROR_KEYWORDS = error_keywords
        self.SERVICE_DOWN_THRESHOLD = service_down_threshold
        self.log_message = log_message
        self.send_mail = send_mail
        self.send_via_hook = send_via_hook
        self.send_slack = send_slack
        self.slack_channel = slack_channel
        self.service_output_file = service_output_file

    def check_host_downtime(self):
        """Identify hosts that have stopped sending data."""
        self.log_message("Checking for Down Hosts...")
        url = f"{self.KIBANA_URL}/metricbeat-*/_search"
        query = {
            "query": {
                "bool": {
                    "must_not": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-5m",
                                    "lt": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 200,
            "_source": ["host.name", "@timestamp"]
        }

        try:
            response = requests.post(url, headers=self.Headers, json=query)
            if response.status_code == 200:
                data = response.json()
                down_hosts = [hit["_source"].get("host", {}).get("name", "unknown") for hit in data.get("hits", {}).get("hits", [])]

                if down_hosts:
                    self.log_message(f"Found {len(down_hosts)} hosts that may be down.")
                    alert_message = f"⚠️ The following hosts have stopped reporting data: {', '.join(down_hosts)}"

                    if self.slack_channel:
                        self.send_slack(message=alert_message)
                    else:
                        self.send_via_hook(alert_message)

                    subject = f"⚠️ Host Downtime Alert: {len(down_hosts)} Hosts Not Reporting"
                    body = "Some hosts have stopped reporting data. Please investigate."
                    self.send_mail(subject=subject, body=body)

                return down_hosts
            else:
                self.log_message(f"Error fetching downtime logs: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log_message(f"Unexpected error while checking downtime: {e}")
            return None

    def check_service_downtime(self):
        """Check if any services are currently down based on Heartbeat data."""
        self.log_message("Checking for Down Services...")
        url = f"{self.KIBANA_URL}/heartbeat-*/_search"  
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-5m",
                                    "lt": "now"
                                }
                            }
                        },
                        {
                            "match": {
                                "monitor.status": "down"
                            }
                        }
                    ]
                }
            },
            "size": 100,
            "_source": [
                "monitor.name",  
                "monitor.id",    
                "url.full",      
                "@timestamp",
                "observer.geo.name"  
            ]
        }

        try:
            response = requests.post(url, headers=self.Headers, json=query)
            if response.status_code == 200:
                data = response.json()
                down_services = []

                for hit in data.get("hits", {}).get("hits", []):
                    service_info = hit.get("_source", {})
                    down_services.append({
                        "name": service_info.get("monitor.name", "Unknown Service"),
                        "id": service_info.get("monitor.id", "N/A"),
                        "url": service_info.get("url.full", "N/A"),
                        "timestamp": service_info.get("@timestamp", "N/A"),
                        "location": service_info.get("observer.geo.name", "Unknown Location")
                    })

                if down_services:
                    self.log_message(f"⚠️ Found {len(down_services)} services that are DOWN.")
                    d = down_services[:5]
                    for service in d:
                        alert_message = "\n".join([
                        f"🔴 Service **{service['name']}** {service['url']} is DOWN!\n"
                        f"🌍 Location: {service['location']}\n"
                        f"🔗 URL: \n"
                        f"🕒 Timestamp: {service['timestamp']}\n"
                        for service in down_services
                        ])

                        if self.slack_channel:
                            self.send_slack(message=alert_message)
                        else:
                            self.send_via_hook(alert_message)
                            self.log_message(f"Service: {service['name']}, ID: {service['id']}, URL: {service['url']}, Timestamp: {service['timestamp']}, Location: {service['location']}")

                    subject = f"⚠️ Service Downtime Alert: {len(down_services)} Services Are Down"
                    body = "The following services have been detected as down:\n" + alert_message
                    self.send_mail(subject=subject, body=body)

                return down_services
            else:
                self.log_message(f"Error fetching service status: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.log_message(f"Network error while checking service downtime: {e}")
            return None
        except Exception as e:
            self.log_message(f"Unexpected error: {e}")
            return None

  