import requests
import time

class Host:
    def __init__(self,kibana_url='',headers={},cpu_threshold=99,log_message=None,send_mail=None,send_via_hook=None,send_slack=None,slack_channel='',host_output_file='hosts.log'):
        self.KIBANA_URL = kibana_url
        self.Headers = headers
        self.CPU_THRESHOLD = cpu_threshold
        self.log_message = log_message
        self.send_mail = send_mail 
        self.send_via_hook = send_via_hook
        self.send_slack = send_slack
        self.slack_channel =slack_channel
        self.host_output_file = host_output_file

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
            "_source": [
                "host.name",
                "@timestamp", 
                "host.ip", 
                "host.os.kernel", 
                "host.os.platform",
                "host.hostname", 
                "host.cpu.usage",
                "system.cpu.user.pct",
                "system.cpu.system.pct",
                "system.cpu.cores",
                "system.memory.actual.used.pct",
                "system.filesystem.used.pct", 
                "system.load.cores",
                "system.load.1",
                "system.memory.page_stats.direct_efficiency.pct"
                ]
        }
        
        try:
            response = requests.post(url, headers=self.Headers, json=query)
            if response.status_code == 200:
                data = response.json()
                self.log_message(f"Found [{len(data['hits']['hits'])}] hosts")
                affected_hosts = []
                affected_host_names = []
                for hit in data["hits"]["hits"]:
                    metadata = hit["_source"] or {}
                    # CPU Usage
                    sys_cores = metadata.get("system", {}).get("cpu", {}).get("cores", "0.00")
                    sys_cpu_usage = metadata.get("system", {}).get("cpu", {}).get("system", {}).get("pct", "0.00")
                    sys_user_usage = metadata.get("system", {}).get("cpu", {}).get("user", {}).get("pct", "0.00")

                    # CPU Normalized Load
                    sys_load = metadata.get("system", {}).get("load", {}).get("1", "unavailable")
                    load_cores = metadata.get("system", {}).get("load", {}).get("cores", "unavailable")

                    # Memory
                    memory_usage = metadata.get("system", {}).get("memory", {}).get("actual", {}).get("used", {}).get("pct", "unknown")

                    # Disk Usage
                    disk_usage = metadata.get("system", {}).get("filesystem", {}).get("used", {}).get("pct", "unknown")

                    #Host Details
                    host = metadata.get("host",{})
                    host_name =  host.get('name','unknown')
                    host_details = f'{host.get("name", "unknown")} - {host.get("os",{}).get("platform","undisclosed")}'
                    cpu_usage = host.get("cpu", {}).get("usage", None)

                    host_dict = {
                        'name': host_name,
                        'timestamp':metadata.get('@timestamp',f'{time.strftime('%Y-%m-%d %H:%M:%S')}'),
                        'sys_cores': sys_cores,
                        'sys_cpu_usage':sys_cpu_usage,
                        'sys_user_usage':sys_user_usage,
                        'sys_load':sys_load,
                        'load_cores':load_cores,
                        'memory_usage':memory_usage,
                        'disk_usage':disk_usage,
                        'platform': host.get('os',{}).get('platform','unknown'),
                        'kernel': host.get('os',{}).get('kernel','unknown'),
                        'cpu_usage':cpu_usage
                    }

                    # Check for hosts exceeding cpu threshold
                    if cpu_usage is not None and type(cpu_usage) == float and host_name not in affected_host_names:
                        if cpu_usage <= 1:
                            cpu_usage *= 100  
                        # Convert to percentage
                        cpu_usage = round(cpu_usage, 4)
                        if cpu_usage > self.CPU_THRESHOLD:
                            host["cpu_usage"] = cpu_usage

                            affected_host_names.append(host.get('name','unknown'))
                            affected_hosts.append(host_dict)
                            
                            # To avoid domain duplication
                            affected_host_names.append(host_name)

                        self.log_message(f"{host_details} - CPU usage:{cpu_usage}% ")
                    else:
                        self.log_message(f"No CPU usage data for {host_details}")
                
                with open(self.host_output_file,'a') as f:
                    if len(affected_hosts) > 0:     
                        # Send Notification
                        for host in affected_hosts:
                            slack_message = f"""
    🔴 High CPU Usage Alert on {host['name']}! ❌ 
                         
    CPU Usage: {float(host.get('cpu_usage',0)) *100}%
    Threshold violation: {self.CPU_THRESHOLD}%
    Sys platform: {host.get('platform','')}
    Sys kernel: {host.get('kernel','')}
    @timestamp: '{ host.get('timestamp','')}'
                        
    # CPU Usage
    System CPU Cores: {host.get("sys_cores",'0')} cores
    System User Usage: {host.get("sys_user_usage","0.00")}
    System Cpu Usage: {host.get("sys_cpu_usage","0.00")}
    CPU USAGE = {(float(host.get("sys_user_usage","0.00")) + float(host.get("sys_cpu_usage","0.00")) ) / float(host.get("sys_cores","0.00")) * 100}%

    # CPU Normalized Load    
    System Load: {host.get("sys_load",'')}
    System Load Cores: {host.get("load_cores",'')}

    # Memory
    Memory Usage: {host.get("memory_usage",'')}%
                        
    # Disk Usage
    Disk Usage: {host.get("disk_usage",'')}%
                        """
                            # Slack notification
                            if self.slack_channel:
                                self.send_slack(message=slack_message)
                            else:
                                self.send_via_hook(slack_message) 

                            # Write to an output file
                            f.write(f"{slack_message} \n")
                            
                    if self.host_output_file:
                        subject = f"🔴 High CPU Usage Detected on [{len(affected_hosts)}] ❌"
                        body = f"CPU usage on {len(affected_hosts)} hosts, exceeded threshold: {cpu_usage}%. Check file attachment for logs"
                        # Send to slack
                        if self.slack_channel:
                            self.send_slack(message=subject, file_path=self.host_output_file)
                        # Send to email 
                        self.send_mail(subject=subject, body=body, attachment=self.host_output_file)
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