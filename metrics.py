import requests
from base import Base
import time

class Metrics(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fetch_data(self, endpoint, query):
        """Fetch data from Elasticsearch."""
        url = f"{self.KIBANA_URL}/{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=query)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log_message(f"Error fetching data: {e}")
            return None

    def notify(self, affected_items, item_type, threshold, notify_limit, log_subject, log_body):
        """Send notifications for affected items."""
        if not affected_items:
            self.log_message(f"[+] Fetching {item_type} Data complete [0] Affected Items...")
            return

        for item in affected_items[:notify_limit]:
            message = self.generate_notification_message(item, item_type, threshold)
            self.brief_notify(message=message)

        if self.USER_LOG_FILE:
            self.write_to_log_file(affected_items, log_subject)
            self.full_notify(subject=log_subject, message=log_body)

        self.log_message(f"Affected {item_type.capitalize()}s: {len(affected_items)}")
        self.log_message(f"[+] Fetching {item_type.capitalize()} Data complete...")

    def generate_notification_message(self, item, item_type, threshold):
        """Generate a notification message based on the item type."""
        if item_type == "latency":
            return f"""
🔴 High Latency Alert On {item['url']} ❌

Timestamp: {item['timestamp']}
Exceeded threshold: {threshold} ms

TCP Latency: {item['tcp']} ms
TLS Latency: {item['tls']} ms
HTTP Latency: {item['http']} ms
            """
        elif item_type == "cpu":
            return f"""
🔴 High CPU Usage Alert on {item['name']}! ❌ 

CPU Usage: {item['cpu_usage']}%
Threshold: {threshold}%
System: {item.get('platform', 'unknown')} | Kernel: {item.get('kernel', 'unknown')}
Timestamp: {item.get('timestamp', '')}

# CPU Usage
System CPU Cores: {item.get('sys_cores', '0')} cores
System User Usage: {item.get('sys_user_usage', '0.00')}
System CPU Usage: {item.get('sys_cpu_usage', '0.00')}
CPU Usage Calculation: {self.calculate_cpu_usage(item)}

# System Load    
System Load: {item.get('sys_load','unavailable')}
System Load Cores: {item.get('load_cores','unavailable')}

# Memory
Memory Usage: {item.get('memory_usage','unknown')}%  

# Disk Usage
Disk Usage: {item.get('disk_usage','unknown')}%  
            """

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

    def fetch_latency_data(self):
        """Fetch latency data from Elasticsearch."""
        self.log_message("[+] Started Fetching Latency Data From Elastic...")
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
        return self.fetch_data("_search", query)

    def process_latency_data(self, data):
        """Process latency data and identify affected hosts."""
        hits = data.get("hits", {}).get("hits", [])
        self.log_message(f"Found [{len(hits)}] services. Checking {self.LATENCY_THRESHOLD} ms threshold...")
        affected_hosts = []
        found_hosts = set()
        for hit in hits:
            source = hit.get("_source", {})
            # Get the Url
            url = source.get("url", {}).get("full", "unknown")
            # Skip if the URL is already processed
            if url in found_hosts:
                continue  
            # Add the URL to the set
            found_hosts.add(url)  
            latency_dict = {
                "url": url,
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

    def fetch_cpu_data(self):
        """Fetch CPU usage data from Elasticsearch."""
        self.log_message("[-] Started fetching CPU Usage Data From Elastic...")
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
        return self.fetch_data("metricbeat-*/_search", query)

    def process_cpu_data(self, data):
        """Process CPU usage data and identify affected hosts."""
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
            cpu_usage = round(cpu_usage, 2)

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
                self.log_message(f"{host_dict['timestamp']} - {host_name} - CPU usage: {cpu_usage}%")

        return affected_hosts

    def get_latency(self):
        """Fetch, process, and notify about high latency."""
        data = self.fetch_latency_data()
        if data:
            affected_hosts = self.process_latency_data(data)
            self.notify(
                affected_hosts,
                "latency",
                self.LATENCY_THRESHOLD,
                self.NOTIFY_LIMIT,
                f"High Latency Detected on {len(affected_hosts)} Hosts",
                f"Latency exceeded threshold on {len(affected_hosts)} hosts. Check attached log.",
            )

    def get_cpu_usage(self):
        """Fetch, process, and notify about high CPU usage."""
        data = self.fetch_cpu_data()
        if data:
            affected_hosts = self.process_cpu_data(data)
            self.notify(
                affected_hosts,
                "cpu",
                self.CPU_THRESHOLD,
                self.NOTIFY_LIMIT,
                f"🔴 High CPU Usage Detected on [{len(affected_hosts)}] Hosts ❌",
                f"CPU usage on {len(affected_hosts)} hosts exceeded {self.CPU_THRESHOLD}%. Check file attachment for logs.",
            )