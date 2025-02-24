# Kibalert
Kibalert is an anomaly monitoring and notification script for Elastic Stack users, especially those using Kibana for visualization. It monitors Elasticsearch data for anomalies, enables custom alerting rules, and sends notifications via email or Slack.

## Prerequisites
- Python 3.x
- Required dependencies installed (see installation section)
- Elastic Kibana API key stored in a `.env` file

## Installation
1. Clone the repository:
   
   **HTTPS**
   ```bash
   git clone https://github.com/briankeny/kibalert.git
   ```
   
   **or SSH**
   ```bash
   git clone git@github.com:briankeny/kibalert.git
   ```
   
   Then navigate to the project directory:
   ```bash
   cd kibalert
   ```

2. Create a Virtual Environment and Install dependencies:
   
   Create a virtual environment:
   ```bash
   python -m venv venv
   ```
   
   Activate it:
   ```bash
   source venv/bin/activate
   ```  
   
   Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file and add the following variables 

   Please Check `.env.example` for full reference:
   
   ```bash
   KIBANA_URL=<your-kibana-url>
   KIBANA_API_KEY=<your-kibana-api-key>
   SMTP_USER=<your-email-client>
   SMTP_PASSWORD=<your-smtp-password-or-key>
   SLACK_TOKEN=<your-slack-bot-token>
   SLACK_CHANNEL=<your-slack-channel>
   ```

## Usage
### 1. Run with Command-Line Arguments
Run the script with the required arguments:
```bash
python main.py -m <receiver_email> [-u <kibana_url>] [-i <rule_id>] [-s <service_id>] [-t <interval>] [-f <log_file>] [-v]
```

#### Command-Line Arguments
| Argument  | Description  | Default  |
|-----------|-------------|----------|
| `-u`, `--url`  | Kibana base URL  | `.env` value |
| `-i`, `--id`  | Rule ID to query data from  | `.env` value or `''` |
| `-s`, `--service`  | Rule ID for service query  | `.env` value or `''` |
| `-m`, `--mail`  | Receiver's email address  | `.env` value or `''` |
| `-ns`, `--notifyslack`  | Notify Slack Channel  | `.env` value or `''` |
| `-st`, `--slacktoken`  | Slack token for API  | `.env` value or `''` |
| `-t`, `--time`  | Sleep interval between checks (seconds)  | `.env` value or `300` |
| `-f`, `--file`  | Log file to save output  | `anomaly.log` |
| `-v`, `--verbose`  | Enable verbose mode  | `.env` value or `True` |
| `-w`, `--webhook`  | Slack webhook URL  | `.env` value or `''` |
| `--smtp_server`  | SMTP server address  | `.env` value or `''` |
| `--smtp_port`  | SMTP port number  | `.env` value or `587` |
| `--smtp_user`  | SMTP username  | `.env` value or `''` |
| `--smtp_password`  | SMTP password  | `.env` value or `''` |
| `--userlog`  | User activity log file  | `user_activity.log` |
| `--hits_size`  | Hits size per query  | `100` |

#### Example Usage
```bash
python main.py -m admin@example.com -t 600 -i 'CPU-THRESHOLD-RULE-ID' -s 'SERVICE-RULE-ID' -v
```
This command sends anomaly reports to `admin@example.com`, checks every 600 seconds, and enables verbose logging.

### 2. Run with Docker
#### Build the Docker image:
```bash
docker build -t kibalert .
```

#### Run the container:
```bash
docker run -d --name kibalert kibalert
```

#### Start/Stop the container:
```bash
docker start kibalert
docker stop kibalert
```

### 3. Run as an Executable Script
Ensure all your environment variables are properly configured

```bash
 python main.py
```

Alternatively

Make the script executable:
```bash
chmod +x main.py
```

Add a shebang line at the beginning of `main.py`: Ensure that the path to your bin/env is correct

```python
#!/usr/bin/env python3
```
Then execute the script directly:
```bash
./main.py 
```

## Logging
Logs are saved to `anomaly.log` (or the specified file) and include timestamps.

## Error Handling
- The script handles unexpected errors and retries after the specified interval.
- Error messages are logged to the console and the log file.

## Contributing
Feel free to fork the repository, make enhancements, and submit pull requests.

## Features
- Fetch host CPU usage alerts
- Fetch service latency alerts
- Log monitoring results to a file
- Send email notifications on detected anomalies
- Send Slack notifications for detected anomalies
- Customizable monitoring interval
- Docker support for easy deployment