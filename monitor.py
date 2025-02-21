import requests
from base import Base


class Monitor(Base):

    def __init__(self, **kwargs):
        # Call parent class's __init__ with all arguments
        super().__init__(**kwargs)
        
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
                                    "gte": f"now-{self.SLEEP_TIME}s",
                                    "lt": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": self.HITS_SIZE,
            "_source": ["host.name", "@timestamp"]
        }

        try:
            response = requests.post(url, headers=self.headers, json=query)
            if response.status_code == 200:
                data = response.json()
                down_hosts = [hit["_source"].get("host", {}).get("name", "unknown") for hit in data.get("hits", {}).get("hits", [])]

                if down_hosts:
                    self.log_message(f"Found {len(down_hosts)} hosts that may be down.")
                    alert_message = f"⚠️ The following hosts have stopped reporting data: {', '.join(down_hosts)}"

                    if self.SLACK_CHANNEL:
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
                                    "gte": f"now-{self.SLEEP_TIME}m",
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
            "size": self.HITS_SIZE,
            "_source": [
                "monitor.name",  
                "monitor.id",    
                "url.full",      
                "@timestamp",
                "observer.geo.name"  
            ]
        }

        try:
            response = requests.post(url, headers=self.headers, json=query)
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
                    # Write down services to a file
                    with open(self.USER_LOG_FILE, "a") as f:
                        for down_service in down_services:
                            for key,val in down_service.items():
                                f.write(f"{key}: {val} \n")
                    
                    for service in down_services[:self.NOTIFY_LIMIT]:
                        alert_message = f"""
                        🔴 Service **{service['name']}** {service['url']} is DOWN!\n"
                        🌍 Location: {service['location']}
                        🕒 Timestamp: {service['timestamp']}\n"""
                        self.brief_notify(alert_message)

                    if self.USER_LOG_FILE:
                        subject = f"⚠️ Service Downtime Alert: {len(down_services)} Services Are Down"
                        body = "The following services have been detected as down: Check attached log file\n"
                        self.full_notify(subject=subject,message=body)
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