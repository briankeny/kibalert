import time
import requests
from base import Base
class Latency(Base):
    def __init__(self, **kwargs):
        # Call parent class's __init__ with all arguments
        super().__init__(**kwargs)
    def fetch_latency_data(self):
            """Fetch latency data from Elastic Search."""
            self.log_message("\n[+] Started Fetching Latency Data From Elastic...")
            url = f"{self.KIBANA_URL}/_search"
            query = {
                "size": self.HITS_SIZE,
                "_source": [
                    "@timestamp",
                    "url.full",
                    "tcp.rtt.connect.us",
                    "tls.rtt.handshake.us",
                    "http.rtt.total.us",
                ],
                "query": {
                    "bool": {
                        "must": [{"range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}s", "lt": "now"}}}],
                        "filter": [{"term": {"monitor.status": "up"}}],
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}],
            }
            
            try:
                response = requests.post(url, headers=self.headers, json=query)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                self.log_message(f"Error fetching latency data: {e}")
                return None

    def process_latency_data(self, data):
        """Process latency data and identify affected hosts."""
        hits = data.get("hits", {}).get("hits", [])
        self.log_message(f"Found [{len(hits)}] services. Checking {self.LATENCY_THRESHOLD} ms threshold...")
        
        affected_hosts = []
        for hit in hits:
            source = hit.get("_source", {})
            latency_dict = {
                "url": source.get("url", {}).get("full", "unknown"),
                "tcp": source.get("tcp", {}).get("rtt", {}).get("connect", {}).get("us", 0) / 1000,
                "tls": source.get("tls", {}).get("rtt", {}).get("handshake", {}).get("us", 0) / 1000,
                "http": source.get("http", {}).get("rtt", {}).get("total", {}).get("us", 0) / 1000,
                "timestamp": source.get("@timestamp", "unknown"),
            }
            
            if any(latency > self.LATENCY_THRESHOLD for latency in [latency_dict["tcp"], latency_dict["tls"], latency_dict["http"]]):
                affected_hosts.append(latency_dict)
                self.log_message(
                    f" {latency_dict['timestamp']}- {latency_dict['url']} | TCP: {latency_dict['tcp']} ms | TLS: {latency_dict['tls']} ms | HTTP: {latency_dict['http']} ms"
                )
        
        return affected_hosts

    def notify_high_latency(self, affected_hosts):
        """Send notifications for high latency services."""
        if not affected_hosts:
            return

        for host in affected_hosts[: self.NOTIFY_LIMIT]:
            message = f"""
🔴 High Latency Alert On {host['url']} ❌

Timestamp: {host['timestamp']}
Exceeded threshold: {self.LATENCY_THRESHOLD} ms

TCP Latency: {host['tcp']} ms
TLS Latency: {host['tls']} ms
HTTP Latency: {host['http']} ms
            """
            self.brief_notify(message=message)
           
        if self.USER_LOG_FILE:
            subject = f"High Latency Detected on {len(affected_hosts)} Hosts"
            body = f"Latency exceeded threshold on {len(affected_hosts)} hosts. Check attached log."
            self.write_to_log_file(affected_hosts,subject)
            self.full_notify(subject=subject,message=body)
        
        self.log_message(f"Affected Services: {len(affected_hosts)} \n")
        self.log_message('[+] Fetching Latency Data complete...')

    def get_latency(self):
        """Main function to fetch, process, and notify about high latency."""
        data = self.fetch_latency_data()
        if data:
            affected_hosts = self.process_latency_data(data)
            self.notify_high_latency(affected_hosts)

class Host(Base):
    def __init__(self, **kwargs):
        # Call parent class's __init__ with all arguments
        super().__init__(**kwargs)

    def get_cpu_usage(self):
        """Fetch CPU usage per inventory item."""
        self.log_message("\n[-] Started fetching CPU Usage Data From Elastic...")
        url = f"{self.KIBANA_URL}/metricbeat-*/_search"
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": f"now-{self.SLEEP_TIME}s", "lt": "now"}}},
                        {"exists": {"field": "host.cpu.usage"}},
                    ]
                }
            },
            "size": self.HITS_SIZE,
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
                "system.memory.page_stats.direct_efficiency.pct",
            ],
        }

        try:
            response = requests.post(url, headers=self.headers, json=query)
            response.raise_for_status()  # Raises an exception for HTTP errors
            data = response.json()

            hits = data.get("hits", {}).get("hits", [])
            self.log_message(f"Found [{len(hits)}] hosts. Checking {self.CPU_THRESHOLD}% threshold...")

            affected_hosts = []
            affected_host_names = set()

            for hit in hits:
                metadata = hit.get("_source", {})
                host = metadata.get("host", {})
                host_name = host.get("name", "unknown")

                cpu_usage = host.get("cpu", {}).get("usage")
                if cpu_usage is None or not isinstance(cpu_usage, float):
                    self.log_message(f"No CPU usage data for {host_name}")
                    continue

                # Convert to percentage
                if cpu_usage <= 1:
                    cpu_usage *= 100  
                
                # Round to 2dp
                cpu_usage = round(cpu_usage,2)

                if cpu_usage >= self.CPU_THRESHOLD and host_name not in affected_host_names:
                    host_dict = {
                        "name": host_name,
                        "timestamp": metadata.get("@timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
                        "platform": host.get("os", {}).get("platform", "unknown"),
                        "kernel": host.get("os", {}).get("kernel", "unknown"),
                        "cpu_usage": cpu_usage,
                        "sys_cores": metadata.get("system", {}).get("cpu", {}).get("cores", "0.00"),
                        "sys_cpu_usage": metadata.get("system", {}).get("cpu", {}).get("system", {}).get("pct", "0.00"),
                        "sys_user_usage": metadata.get("system", {}).get("cpu", {}).get("user", {}).get("pct", "0.00"),
                        "sys_load": metadata.get("system", {}).get("load", {}).get("1", "unavailable"),
                        "load_cores": metadata.get("system", {}).get("load", {}).get("cores", "unavailable"),
                        "memory_usage": metadata.get("system", {}).get("memory", {}).get("actual", {}).get("used", {}).get("pct", "unknown"),
                        "disk_usage": metadata.get("system", {}).get("filesystem", {}).get("used", {}).get("pct", "unknown"),
                    }

                    affected_hosts.append(host_dict)
                    affected_host_names.add(host_name)

                    if self.VERBOSE:
                     self.log_message(f"{host_dict['timestamp']} - {host_name} - CPU usage: {cpu_usage}%")

            if affected_hosts:
                self.notify_high_cpu_usage(affected_hosts)

            return data

        except requests.exceptions.RequestException as e:
            self.log_message(f"Network error while fetching CPU usage: {e}")
        except ValueError as e:
            self.log_message(f"JSON decode error: {e}")
        except Exception as e:
            self.log_message(f"Unexpected error: {e}")

        return None

    def notify_high_cpu_usage(self, affected_hosts):
        """Send notifications for high CPU usage."""
        if not affected_hosts:
            self.log_message(f"[+] Fetching CPU Usage Data complete [0] Affected Hosts...")
            return
        for host in affected_hosts[: self.NOTIFY_LIMIT]:
            message = f"""
🔴 High CPU Usage Alert on {host['name']}! ❌ 

CPU Usage: {host['cpu_usage']}%
Threshold: {self.CPU_THRESHOLD}%
System: {host.get('platform', 'unknown')} | Kernel: {host.get('kernel', 'unknown')}
Timestamp: {host.get('timestamp', '')}

# CPU Usage
System CPU Cores: {host.get('sys_cores', '0')} cores
System User Usage: {host.get('sys_user_usage', '0.00')}
System CPU Usage: {host.get('sys_cpu_usage', '0.00')}
CPU Usage Calculation: {self.calculate_cpu_usage(host)}

# System Load    
System Load: {host.get('sys_load','unavailable')}
System Load Cores: {host.get('load_cores','unavailable')}

# Memory
Memory Usage: {host.get('memory_usage','unknown')}%  

# Disk Usage
Disk Usage: {host.get('disk_usage','unknown')}%  
"""             
            self.brief_notify(message=message)
        
       
        if self.USER_LOG_FILE:
            subject = f"🔴 High CPU Usage Detected on [{len(affected_hosts)}] Hosts ❌" 
            body = f"CPU usage on {len(affected_hosts)} hosts exceeded {self.CPU_THRESHOLD}%. Check file attachment for logs."
            self.write_to_log_file(affected_hosts,subject)
            self.full_notify(subject=subject,message=body)
       
        self.log_message(f"Affected Hosts: {len(affected_hosts)}")
        self.log_message('[+] Fetching CPU Data complete...\n\n')

    @staticmethod
    def calculate_cpu_usage(host):
        """Calculate CPU usage percentage based on system and user usage."""
        try:
            sys_usage = float(host.get("sys_cpu_usage", "0.00"))
            user_usage = float(host.get("sys_user_usage", "0.00"))
            cores = float(host.get("sys_cores", "1"))
            return round((sys_usage + user_usage) / cores * 100, 2)
        except (ValueError, ZeroDivisionError):
            return "N/A"