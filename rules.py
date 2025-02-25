import requests
import time
from base import Base

class Rule(Base):
    def __init__(self, **kwargs):
        # Call parent class's __init__ with all arguments
        super().__init__(**kwargs)
        
    def _fetch_alerts(self, rule_id):
        """Fetch alerts from Kibana based on rule ID."""
        query = {
            "query": {
                "bool": {
                    "must": [{"term": {"kibana.alert.rule.uuid": rule_id}}],
                    "filter": [{"range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}s", "lte": "now"}}}]
                }
            },
            "size": self.HITS_SIZE
        }
        
        try:
            response = requests.post(self.KIBANA_RULE_URL, headers=self.headers, json=query)
            response.raise_for_status()
            return response.json().get('hits', {}).get('hits', [])
        except requests.RequestException as e:
            self.log_message(f'Error fetching alerts: {e}')
            return []
    
    def _process_alerts(self, alerts, is_host_alert=True):
        """Process alerts and extract relevant information."""
        alerts = alerts or []
        self.log_message('Found {} alerts'.format(len(alerts)))
        extracted_data = []
        for alert in alerts:
            alert_source = alert.get('_source', {})
            data = {
                "name": alert_source.get('host.name' if is_host_alert else 'service.name', ''),
                "alert_status": alert_source.get('kibana.alert.status', 'unknown'),
                "features": alert_source.get('kibana.alert.rule.consumer', ''),
                "started": alert_source.get('kibana.alert.start', ''),
                "rule_name": alert_source.get('kibana.alert.rule.name', ''),
                "rule_category": alert_source.get('kibana.alert.rule.category', ''),
                "alert_reason": alert_source.get('kibana.alert.reason', ''),
                "timestamp": alert_source.get('@timestamp', time.strftime('%Y-%m-%d %H:%M:%S')),
                "threshold": alert_source.get('kibana.alert.evaluation.threshold', ''),
            }
            if is_host_alert:
                data.update({
                    "platform": alert_source.get('host.os.platform', ''),
                    "version": alert_source.get('host.os.version', ''),
                    "os": alert_source.get('host.os.type', ''),
                    "kernel": alert_source.get('host.os.kernel', ''),
                    "resource_type": alert_source.get('kibana.alert.rule.producer', ''),
                })
            else:
                data.update({
                    "language": alert_source.get('service.language.name', ''),
                    "transaction_type": alert_source.get('transaction.type', ''),
                    "service_environment": alert_source.get('service.environment', ''),
                })
            extracted_data.append(data)
        return extracted_data
    
    def _send_notifications(self, alerts, is_host_alert=True):
        """Send notifications via email and Slack."""
        if not alerts:
            return

        for alert in alerts[: self.NOTIFY_LIMIT]:
                message = f"""
🔴 {alert['rule_name']} Rule Alert for {alert['name']} ❌

Alert Status: {alert['alert_status']}
Entity: {alert['name']}
Started: {alert['started']}
Timestamp: {alert['timestamp']}
Threshold: {alert['threshold']}

Reason: {alert['alert_reason']}
Rule Category: {alert['rule_category']}
Features: {alert['features']}
                """
               
                self.brief_notify(message=message)
        
        if self.USER_LOG_FILE:        
            subject = f"Rule Alert for {'CPU Usage' if is_host_alert else 'Latency'} Detected on {len(alerts)} {'hosts' if is_host_alert else 'services'}"
            body = f"{'CPU usage' if is_host_alert else 'Latency'} exceeded threshold. A file with logs is attached."
            self.write_to_log_file(alerts,subject)
            self.full_notify(subject=subject,message=body)
       
        if self.VERBOSE:
            for alert in alerts:
                self.log_message(f"{alert['timestamp']} - {alert['name']} - {alert['alert_reason']} - {alert['alert_status']}")

        self.log_message(f"[+] Fetching {'Host' if is_host_alert else 'services'} Alerts complete. Concluded {len(alerts)} ...")    
    
    def fetch_host_alerts(self):
        """Fetch and process alerts for host CPU usage."""
        if not self.HOSTS_RULE_IDS:
            self.log_message('[-] HOSTS_RULE_IDS not found. Skipping rule alerts.')
            return
        for host_rule in self.HOSTS_RULE_IDS:
            self.log_message(f'[-]  Fetching alerts for HOST CPU Usage from rule {host_rule} started...')
            alerts = self._fetch_alerts(host_rule)
            processed_alerts = self._process_alerts(alerts, is_host_alert=True)
            self._send_notifications(processed_alerts, is_host_alert=True)
    
    def fetch_service_alerts(self):
        """Fetch and process alerts for service latency."""
        if not self.SERVICE_RULE_IDS:
            self.log_message('[-] SERVICE_RULE_IDS not found. Skipping rule alerts.')
            return
        for service_rule in self.SERVICE_RULE_IDS:
            self.log_message(f'[-]  Fetching alerts for Latencies Exceeded alerts from rule {service_rule} started...')
            alerts = self._fetch_alerts(service_rule)
            processed_alerts = self._process_alerts(alerts, is_host_alert=False)
            self._send_notifications(processed_alerts, is_host_alert=False)