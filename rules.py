import requests
import json
import time

class Rule:
    def __init__(self, rule_id='',service_id='',cpu_threshold=99,headers={},kibana_url='',log_message=None,send_mail=None,send_slack=None,slack_channel=None,send_via_hook=None,rules_file='rules.log'):
        self.ANOMALY_RULE_ID = rule_id
        self.Headers = headers
        self.CPU_THRESHOLD = cpu_threshold
        self.KIBANA_URL = kibana_url
        self.log_message = log_message
        self.send_mail = send_mail
        self.SERVICE_ID = service_id
        self.send_slack = send_slack
        self.slack_channel = slack_channel
        self.send_via_hook = send_via_hook
        self.rules_file = rules_file
    
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
                    alert_status = {alert_source.get('kibana.alert.status','unknown')}
                    features = alert_source.get('kibana.alert.rule.consumer','')
                    alert_status = alert_source.get('kibana.alert.status','unknown')
                    started = alert_source.get('kibana.alert.start','')
                    rule_category = alert_source.get('kibana.alert.rule.category','')
                    rule_name = alert_source.get('kibana.alert.rule.name','')
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
                            "alert_status":alert_status, 
                            "features":features, 
                            "started":started,
                            "rule_name":rule_name,
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
                              
                    with open(self.rules_file,'a') as f:
                        for host in affected_hosts:
                            slack_message = f"""
    🔴 {host.get('rule_name','')} rule Alert for {host.get('host_name','')} ❌ 
                    
    Alert Status: {host.get('alert_status','')}
    Host : {host.get('host_name','')}
    Started :   {host.get('started')}
    Timestamp : {host.get('timestamp','')}
    
    Reason  :   {host.get('alert_reason','')}
                 
    Rule Category:  {host.get('rule_category')} 
    Features:    {host.get('features')}

                           """ 
                            f.write(f'{slack_message} \n')
                            if self.slack_channel:
                                self.send_slack(message=slack_message)
                            else:
                                self.send_via_hook(slack_message)

                    """Send slack and email notifications"""

                    subject = f"High CPU Usage Detected on {len(affected_hosts)} hosts "
                    body = f"CPU usage on {len(affected_hosts)} exceeded threshold: {self.CPU_THRESHOLD}%. A file with the log information has been attached"
                    
                    self.send_mail(subject=subject, 
                                   body=body, 
                                   attachment=self.log_message)
                    
                    if self.slack_channel:
                     self.send_slack(message=body, file_path=self.rules_file)
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
            "size": 100
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
                    alert_status = {alert_source.get('kibana.alert.status','unknown')}
                    features = alert_source.get('kibana.alert.rule.consumer','')
                    alert_status = alert_source.get('kibana.alert.status','unknown')
                    started = alert_source.get('kibana.alert.start','')
                    rule_category = alert_source.get('kibana.alert.rule.category','')
                    rule_name = alert_source.get('kibana.alert.rule.name','')
                    latency_threshold = alert_source.get('kibana.alert.evaluation.threshold','')
                    alert_reason = alert_source.get('kibana.alert.reason','')
                    language = alert_source.get('service.language.name','')
                    alert_instance = alert_source.get('kibana.alert.instance.id','')
                    processor_event = alert_source.get('processor.event','')
                    service_name = alert_source.get('service.name','')
                    service_environment = alert_source.get('service.environment','')
                    transaction_type = alert_source.get('transaction.type')
                    timestamp = alert_source.get('@timestamp',f'{time.strftime('%Y-%m-%d %H:%M:%S')}')

                    data = {
                        'service_name':service_name,
                        'alert_status':alert_status,
                        'features':features,
                        'rule_name':rule_name,
                        'latency_threshold':latency_threshold,
                        'started':started,
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
                    with open(self.rules_file, 'a') as f:
                        f.write('---- \n')
                        for svc in affected_services:
                            message = f"""
    🔴 {svc.get('rule_name','')} Rule Alert for {svc.get('service_name','')} ❌ 
                    
    Alert Status: {svc.get('alert_status','')}
    Host : {svc.get('service_name','')}
    Timestamp : {svc.get('timestamp','')}
    Started :   {svc.get('started','')}   
    Latency Threshold :  {svc.get('latency_threshold','')} ms
    
    Reason  :   {svc.get('alert_reason','')}

    Language : {svc.get('language','')}
    Transaction: {svc.get('transaction_type')}
    
    Features:    {svc.get('features')}
    Rule Category:  {svc.get('rule_category')} 
                                \n
                            """
                            f.write(f'{message} \n')
                            if self.slack_channel:
                                self.send_slack(message=message)
                            else:
                                self.send_via_hook(message)
                    """Send email / slack notification"""
                    body = f"Latency on {len(affected_services)} services exceeded limit. Check file attachment."
                    subject = f"🔴 High Latency Detected on {len(affected_services)} Services ❌" 
                    self.send_mail(subject=subject, 
                                   body=body, 
                                   attachment=self.rules_file)                
                    if self.slack_channel:
                     self.send_slack(message=body, file_path=self.rules_file)
                    self.log_message(f"\t Affected : {len(affected_services)}")
            else:
                self.log_message(f"Failed to fetch alert data: {response.status_code} - {response.text}")
    
        except Exception as e:
            self.log_message(f'Error fetching alerts: {e}')