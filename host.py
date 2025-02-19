import requests
import time

class Host:
    def __init__(self,kibana_url='',headers={},cpu_threshold=95,log_message=None,send_mail=None):
        self.KIBANA_URL = kibana_url
        self.Headers = headers
        self.CPU_THRESHOLD = cpu_threshold
        self.log_message = log_message
        self.send_mail = send_mail 

    def get_cpu_usage(self):
        """Fetch CPU usage per inventory item."""
        self.log_message("Fetching CPU Usage Data From Elastic...")
        url = f"{self.KIBANA_URL}/metricbeat-*/_search"
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
                            "exists": {
                                "field": "host.cpu.usage"
                            }
                        }
                    ]
                }
            },
            "size": 200,
            "_source": ["host.name", "host.ip", "host.os.kernel", "host.os.platform", "host.hostname", "host.cpu.usage", "system.cpu.cores"]
        }
        
        try:
            response = requests.post(url, headers=self.Headers, json=query)
            if response.status_code == 200:
                data = response.json()
                self.log_message(f"\t  Found [{len(data['hits']['hits'])}]")
                affected_hosts = []
                for hit in data["hits"]["hits"]:
                    score = hit["_score"]
                    host = hit["_source"]["host"]
                    host_details = f'{host["name"]} - {host["os"]["platform"]} - {host["os"]["kernel"]}'
                    # cores = host["system"]["cpu"]["cores"]
                    cpu_usage = host.get("cpu", {}).get("usage", None)

                    host_dict = {
                        'name': host['name'],
                        'ips': host['ip'],
                        'platform': host['os']['platform'],
                        'kernel': host['os']['kernel'],
                        'cpu_usage':cpu_usage
                    }
                   
                    if cpu_usage is not None and type(cpu_usage) == float:
                        if cpu_usage <= 1:
                            cpu_usage *= 100  
                        # Convert to percentage
                        cpu_usage = round(cpu_usage, 2)
                        if cpu_usage > self.CPU_THRESHOLD:
                            affected_hosts.append(host_dict)
                        self.log_message(f"{host_details} - CPU usage:{cpu_usage}%  Score: {score} ")
                    else:
                        self.log_message(f"No CPU usage data for {host_details}")
                
                if len(affected_hosts) > 0:
                    subject = f"High CPU Usage Detected on [{len(affected_hosts)}] "
                    body = f"CPU usage on {len(affected_hosts)} hosts, exceeded threshold: {cpu_usage}%. Check file attachment"
                   
                    # Create a file with the affected 
                    with open('affected_hosts.txt', 'w') as f:
                        for host in affected_hosts:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {host['name']} - {host['ip']} - {host['os']} - {host['kernel']} {host['cpu_usage']} \n")
                            
                    self.send_mail(subject=subject, body=body, attachment='affected_hosts.txt')
                    self.log_message(f"\t Affected : {len(affected_hosts)}")
                
                return data
            else:
                self.log_message(f"Error fetching CPU usage: {response.status_code} - {response.text}")
                return None
            
        except requests.exceptions.RequestException as e:
            self.log_message(f"Network error while fetching CPU usage: {e}")
            return None
        except ValueError as e:
            self.log_message(f"JSON decode error: {e}")
            return None
        except Exception as e:
            self.log_message(f"Unexpected error: {e}")
            return None

        
        