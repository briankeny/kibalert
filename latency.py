import requests
import time

class Latency:
    def __init__(self, url,filename='latency_anomaly.txt',latency_threshold=1200,headers={}, log_message=None,  send_mail=None):
        # Kibana configuration
        self.KIBANA_URL = url
        self.LATENCY_THRESHOLD  =latency_threshold
        self.Headers = headers
        self.send_mail = send_mail
        self.log_message = log_message
        self.filename = filename
    
    def get_latency(self):
        self.log_message("Fetching Latency Data From Elastic...")
        """Fetch latency data per inventory item."""
        url = f"{self.KIBANA_URL}/_search"         
        # Updated query to fetch relevant latency fields
        query = {
            "size": 1000,
            "_source": [
                "@timestamp",
                "url.full",
                "tcp.rtt.connect.us",
                "tls.rtt.handshake.us",
                "http.rtt.total.us"
            ],
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
                        }
                    ],
                    "filter": [
                        {
                            "term": {
                                "monitor.status": "up"
                            }
                        }
                    ]
                }
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }

        try:
            response = requests.post(url, headers=self.Headers, json=query)
            if response.status_code == 200:
                data = response.json()
                self.log_message(f"\t  Found [{len(data['hits']['hits'])}]")
                affected_hosts =[]
                for hit in data["hits"]["hits"]:
                    source = hit["_source"]
                    url = source["url"]["full"]
                    tcp_latency = source.get("tcp", {}).get("rtt", {}).get("connect", {}).get("us", 0) / 1000  # Convert to ms
                    tls_latency = source.get("tls", {}).get("rtt", {}).get("handshake", {}).get("us", 0) / 1000  # Convert to ms
                    http_latency = source.get("http", {}).get("rtt", {}).get("total", {}).get("us", 0) / 1000  # Convert to ms
                    latency_dict = {
                        'url': url,
                        'tcp': tcp_latency,
                        'tls': tls_latency,
                        'http': http_latency
                    }

                    if tcp_latency > self.LATENCY_THRESHOLD or tls_latency > self.LATENCY_THRESHOLD or http_latency > self.LATENCY_THRESHOLD:
                        affected_hosts.append(latency_dict)

                    self.log_message(f"{url} | TCP Latency: {tcp_latency} ms | TLS Handshake: {tls_latency} ms | HTTP Latency: {http_latency} ms")
                
                if len(affected_hosts) > 0:
                    subject = f"High Latency Detected on {len(affected_hosts)} Hosts"
                    body = f"Latency on {len(affected_hosts)}: exceeded threshold: {self.LATENCY_THRESHOLD}% .Check file attachment"              
                    with open(self.filename, 'w') as f:
                        for host in affected_hosts:
                            url = host['url']
                            tcp_latency = host['tcp']
                            tls_latency = host['tls']
                            http_latency = host['http']
                            body = f"{url}: exceeded threshold - Tcp: {tcp_latency} ms - Tls: {tls_latency} ms - Http: {http_latency} ms {tcp_latency}%"
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Host: {url} | TCP Latency: {tcp_latency} ms | TLS Handshake: {tls_latency} ms | HTTP Latency: {http_latency} ms \n")
                    self.send_mail(subject=subject, body=body, attachment=self.filename)
                    self.log_message(f"\t Affected : {len(affected_hosts)}")
                return data
            else:
                self.log_message(f"Error fetching latency: {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            self.log_message(f"Error fetching latency: {e}")
            return None
    
   