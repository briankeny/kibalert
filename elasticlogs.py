import requests
from base import Base

class  ElasticLogs(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fetch_logs(self):
        """Fetch logs from logs-* index, extract meaningful fields, and alert if a message is present."""
        self.log_message("[-] Fetching logs from logs-* index...")
        url = f"{self.KIBANA_URL}/logs-*/_search"
        query = {
            "query": {
                "range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}m", "lt": "now"}}
            },
            "size": self.HITS_SIZE
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=query)
            if response.status_code != 200:
                self.log_message(f"Error fetching logs: {response.status_code} - {response.text}")
                return None
            
            logs_data = response.json().get("hits", {}).get("hits", [])
            return self.process_logs(logs_data)
        except requests.exceptions.RequestException as e:
            self.log_message(f"Network error while fetching logs: {e}")
        except Exception as e:
            self.log_message(f"Unexpected error while fetching logs: {e}")
        return None

    def process_logs(self, logs_data):
        """Extracts necessary fields from logs and alerts if a message is found."""
        extracted_logs = []
        count = 0
        for log in logs_data:
            log_source = log.get("_source", {})
            extracted_log = {
                "timestamp": log_source.get("@timestamp", "N/A"),
                "agent": log_source.get("agent", {}).get("name", "N/A"),
                "version": log_source.get("agent", {}).get("version", "N/A"),
                "culprit": log_source.get("error", {}).get("culprit", "Unknown"),
                "exception_code": log_source.get("error", {}).get("exception", [{}])[0].get("code", "N/A"),
                "exception_message": log_source.get("error", {}).get("exception", [{}])[0].get("message", "No message"),
                "service_name": log_source.get("service", {}).get("name", "Unknown"),
                "service_env": log_source.get("service", {}).get("environment", "N/A"),
                "hostname": log_source.get("host", {}).get("name", "Unknown"),
                "host_ip": log_source.get("host", {}).get("ip", ["N/A"])[0],
                "runtime": log_source.get("service", {}).get("runtime", {}).get("name", "Unknown"),
                "runtime_version": log_source.get("service", {}).get("runtime", {}).get("version", "N/A"),
                "url": log_source.get("url", {}).get("full", "N/A"),
                "transaction": log_source.get("transaction", {}).get("name", "N/A"),
                "message": log_source.get("message", "")
            }
            extracted_logs.append(extracted_log)
            
            if count < self.NOTIFY_LIMIT and extracted_log["message"]:
                self.alert_log_issue(extracted_log)
    
            self.log_message(f"{extracted_log['timestamp']} - {extracted_log['service_name']} - {extracted_log['culprit']} - {extracted_log['exception_code']} - {extracted_log['exception_message']}")

            count += 1

        self.save_logs(extracted_logs)
        self.log_message('[-] Logs processing completed.')
        return extracted_logs

    def alert_log_issue(self, log_data):
        """Triggers an alert if a log message is found."""
        alert_message = f"""
        🔴 Log Alert! Issue detected:
        📅 Timestamp: {log_data['timestamp']}
        💻 Host: {log_data['hostname']} ({log_data['host_ip']})
        📌 Service: {log_data['service_name']} [{log_data['service_env']}]
        ⚙️ Runtime: {log_data['runtime']} v{log_data['runtime_version']}
        🌐 URL: {log_data['url']}
        🛠️ Culprit: {log_data['culprit']}
        ❗ Exception: {log_data['exception_code']} - {log_data['exception_message']}
        📝 Log Message: {log_data['message']}
        """
        
        self.brief_notify(alert_message)
        return
    
    def save_logs(self, logs):
        """Save logs for further analysis."""
        
        if not logs:
            self.log_message("No logs found for further analysis.")
            return
       
        
        self.log_message(f"Saving {len(logs)} logs for further analysis.")
    
        if self.USER_LOG_FILE:
            subject = "📌 Logs Collected for further Analysis"
            body = "Attached log file contains error logs for analysis."
            self.write_to_log_file(logs,subject)
            self.full_notify(subject=subject, message=body)
            self.send_mail(subject=subject, body=body)
            