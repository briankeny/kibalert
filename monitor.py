import requests
from base import Base

class Monitor(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fetch_downtime_data(self, index: str, query: dict, source_fields: list):
        """Generic method to fetch downtime data from Kibana."""
        self.log_message(f"[-] Checking for downtime in {index}...")
        url = f"{self.KIBANA_URL}/{index}/_search"
        query["_source"] = source_fields

        try:
            response = requests.post(url, headers=self.headers, json=query)
            if response.status_code == 200:
                return response.json().get("hits", {}).get("hits", [])
            else:
                self.log_message(f"Error fetching {index} downtime logs: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            self.log_message(f"Network error while fetching {index} downtime: {e}")
        except Exception as e:
            self.log_message(f"Unexpected error while fetching {index} downtime: {e}")
        return None

    def process_downtime(self, downtime_data=[], entity_key=''):
        """Process downtime data and extract unique entities."""
        if not downtime_data:
            self.log_message("No downtime data found.")
            return []
        
        unique_entities = []
        unique_entity_names = set()
        for hit in downtime_data:
            entity_info = hit.get("_source", {})
            entity_name = entity_info.get(entity_key,{}).get("name", "Unknown")
            if entity_name not in unique_entity_names:
                if entity_key == 'monitor':
                    unique_entities.append({
                            "name": entity_info.get("monitor",{}).get("name", "Unknown Service"),
                            "id": entity_info.get("monitor",{}).get("id", "N/A"),
                            "url": entity_info.get("url",{}).get("full", "N/A"),
                            "timestamp": entity_info.get("@timestamp", "N/A"),
                            "location": entity_info.get("observer",{}).get("geo",{}).get("name", "Unknown Location")
                    })
                   
                else:
                    unique_entities.append({
                        "name": entity_info.get("host",{}).get("name", "Unknown Host"),
                        "timestamp": entity_info.get("@timestamp", "N/A"),
                    })
                unique_entity_names.add(entity_name)
        return unique_entities

    def notify_downtime(self, downtime_list, entity_type):
        """Handles notifications and alerts for downtime entities."""
        if not downtime_list:
            self.log_message(f"[+] No {entity_type}(s) are DOWN.")
            return

        count = len(downtime_list)
        self.log_message(f"⚠️ Found {count} {entity_type}(s) that are DOWN.")
       
        for entity in downtime_list[:self.NOTIFY_LIMIT]:
            alert_message = f"""
            🔴 Siren Alert! {entity_type.capitalize()} **{entity['name']}** is DOWN!
            🌍 Location: {entity.get('location', 'Unknown')}
            🕒 Timestamp: {entity.get('timestamp', 'N/A')}
            🔗 ID: {entity.get('id', 'N/A')}
            """
            self.brief_notify(alert_message)

        if self.USER_LOG_FILE:
            subject = f"⚠️ Downtime Alert: {count} {entity_type.capitalize()}(s) Are Down"
            body = "Check attached log file\n"
            self.write_to_log_file(downtime_list,subject)
            self.full_notify(subject=subject, message=body)
            self.send_mail(subject=subject, body=body)

        for entity in downtime_list:
            self.log_message(f"{entity.get('timestamp', 'N/A')} - {entity.get('name', 'Unknown')} is DOWN.")

        self.log_message(f"[+] Fetching {entity_type} Downtime complete... {count} \n")

    def check_host_downtime(self):
        """Identify hosts that have stopped sending data."""
        query = {
            "query": {
                "bool": {
                    "must_not": [
                        {"range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}s", "lt": "now"}}}
                    ]
                }
            },
            "size": self.HITS_SIZE
        }
        source_fields = ["host.name","@timestamp"]
        downtime_data = self.fetch_downtime_data("metricbeat-*",query,source_fields)
        if downtime_data is None:
            return None

        down_hosts = self.process_downtime(downtime_data, "host")
        self.notify_downtime(down_hosts, "host")
        return down_hosts

    def check_service_downtime(self):
        """Check if any services are currently down based on Heartbeat data."""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}m", "lt": "now"}}},
                        {"match": {"monitor.status": "down"}}
                    ]
                }
            },
            "size": self.HITS_SIZE
        }
        source_fields = [ "monitor.name", "monitor.id","url.full","@timestamp","observer.geo.name"]
        downtime_data = self.fetch_downtime_data("heartbeat-*", query,source_fields)
        if downtime_data is None:
            return None
        down_services = self.process_downtime(downtime_data, "monitor")
        self.notify_downtime(down_services, "service")
        return down_services