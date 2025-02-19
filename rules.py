import requests
import json
import time

class Rule:
    def __init__(self, rule_id='',service_id='',cpu_threshold=95,headers={},kibana_url='',log_message=None,send_mail=None):
        self.ANOMALY_RULE_ID = rule_id
        self.Headers = headers
        self.CPU_THRESHOLD = cpu_threshold
        self.KIBANA_URL = kibana_url
        self.log_message = log_message
        self.send_mail = send_mail
        self.SERVICE_ID = service_id
    
    def fetch_host_alerts(self):
        self.log_message(f'Fetching alerts for HOST CPU Usage from rule {self.ANOMALY_RULE_ID} started...')  
        url = f"{self.KIBANA_URL}/.alerts-*/_search"  
        # The query to find alerts tied to a specific rule
        query = {
            "query": {
                "bool": {
                    "must": [
                    {
                        "term": {
                            "kibana.alert.rule.uuid": f"{self.ANOMALY_RULE_ID}"
                        }
                    }
                ],
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-1h",  
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 1000 
        }

        try:
            # Send the query to Elasticsearch
            response = requests.post(url, headers=self.Headers, data=json.dumps(query))
            if response.status_code == 200:
                data = response.json()
                alerts = data.get('hits', {}).get('hits', [])
                affected_hosts = []
                for alert in alerts:
                    alert_source = alert.get('_source', {})
                    host_name = alert_source.get('host.hostname','')
                    platform = alert_source.get('host.os.platform','')
                    version = alert_source.get('host.os.version','')
                    name = alert_source.get('host.name','')
                    os = alert_source.get('host.os.type','')
                    kernel = alert_source.get('host.os.kernel','')
                    alert_reason = alert_source.get('kibana.alert.reason','')
                    rule_category = alert_source.get('kibana.alert.rule.category','')
                    timestamp = alert_source.get('@timestamp','')
                    resource_type = alert_source.get('kibana.alert.rule.producer','')
                    data = {
                            "host_name":host_name, 
                            "platform":platform , 
                            "version":version, 
                            "rule_category":rule_category,
                            "timestamp":timestamp,
                            "alert_reason":alert_reason,
                            "name":name, 
                            "os":os,
                            "kernel":kernel,
                            "resource_type":resource_type
                    }
                    affected_hosts.append(data)
                    self.log_message(f"{timestamp} - {host_name} - {alert_reason}")
                
                if len(affected_hosts) > 0 :
                    # Send email notification
                    body = f"CPU usage on {len(affected_hosts)} exceeded threshold: {self.CPU_THRESHOLD}%. A file with the log information has been attached"
                    subject = f"High CPU Usage Detected on {len(affected_hosts)} "              
                    with open('critical.txt', 'w') as f:
                        for host in affected_hosts:
                            desc = ''
                            if host:
                                for key, val in host.items():
                                    desc += f"{key}: {val} \t"
                            if desc:
                                f.write(f'{desc} \n\n')

                    self.send_mail(subject=subject, 
                                   body=body, 
                                   attachment='critical.txt')
                    self.log_message(f"\t Affected : {len(affected_hosts)}")
            else:
                self.log_message(f"Failed to fetch alert data: {response.status_code} - {response.text}")
    
        except Exception as e:
            self.log_message(f'Error fetching alerts: {e}')

    def fetch_service_alerts(self):
        self.log_message(f'Fetching alerts for Latencies Exceeded alerts from rule {self.SERVICE_ID} started...')  
        url = f"{self.KIBANA_URL}/.alerts-*/_search"  
        # The query to find alerts tied to a specific rule
        query = {
            "query": {
                "bool": {
                    "must": [
                    {
                        "term": {
                            "kibana.alert.rule.uuid": f"{self.SERVICE_ID}"
                        }
                    }
                ],
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-20m",  
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 1000 
        }

        try:
            # Send the query to Elasticsearch
            response = requests.post(url, headers=self.Headers, data=json.dumps(query))
            if response.status_code == 200:
                data = response.json()
                alerts = data.get('hits', {}).get('hits', [])
                affected_services =[]
                for alert in alerts:
                    alert_source = alert.get('_source', {})
                    
                    alert_reason = alert_source.get('kibana.alert.reason','')
                    language = alert_source.get('service.language.name','')
                    alert_instance = alert_source.get('kibana.alert.instance.id','')
                    processor_event = alert_source.get('processor.event','')
                    service_name = alert_source.get('service.name','')
                    service_environment = alert_source.get('service.environment','')
                    transaction_type = alert_source.get('transaction.type')
                    rule_category = alert_source.get('Latency threshold','')
                    timestamp = alert_source.get('@timestamp',f'{time.strftime('%Y-%m-%d %H:%M:%S')}')

                    data = {
                        'service_name':service_name,
                        'alert_reason':alert_reason,
                        'language':language,
                        'alert_instance':alert_instance,
                        'processor_event':processor_event,
                        'service_environment':service_environment,
                        'transaction_type':transaction_type,
                        'rule_category':rule_category,
                        'timestamp':timestamp
                    }

                    affected_services.append(data)
                    self.log_message(f"{timestamp} - {service_name} - {alert_reason}")
              
                if len(affected_services) > 0 :
                    """Send email notification"""
                    body = f"Latency on {len(affected_services)} exceeded limit of 1500ms. A file with the log information has been attached"
                    subject = f"High Latency Detected on {len(affected_services)} Services"              
                    with open('latency.txt', 'w') as f:
                        for svc in affected_services:
                            desc = ''
                            if svc:
                                for key, val in svc.items():
                                    desc += f"{key}: {val} \t"
                            if desc:
                                f.write(f'{desc} \n\n')

                    self.send_mail(subject=subject, 
                                   body=body, 
                                   attachment='latency.txt')
                    self.log_message(f"\t Affected : {len(affected_services)}")
            else:
                self.log_message(f"Failed to fetch alert data: {response.status_code} - {response.text}")
    
        except Exception as e:
            self.log_message(f'Error fetching alerts: {e}')