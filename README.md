# Kibalert
Kibalert is an anomaly monitoring and notification script for Elastic Stack users, especially those using Kibana for visualization. It monitors Elasticsearch data for anomalies, enables custom alerting rules, and sends notifications via email or other channels. 

Designed for simplicity and flexibility.

## Description
This script monitors anomalies in system metrics such as CPU usage and service latency using Elastic Kibana. It sends notifications via email when anomalies are detected and logs the results in a file.

## Features
- Fetch host CPU usage alerts
- Fetch service latency alerts
- Log monitoring results to a file
- Send email notifications on detected anomalies
- Customizable monitoring interval

## Prerequisites
- Python 3.x
- Required dependencies installed (see installation section)
- Elastic Kibana API key stored in a `.env` file

## Installation
1. Clone the repository:
   
   HTTPS

   ```bash
   git clone https://github.com/briankeny/kibalert.git
  
   ```
   or SSH

   ```bash
      git clone git@github.com:briankeny/kibalert.git
   ```
   Then

   ```bash
   cd kibalert
   ```

2. Create a Virtual Environment and Install dependencies:
   
   Create

   ```bash
      python -m venv venv 
   ```
   Activate

   ```bash
      source venv/bin/activate
   ```  
   Install requirements

   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add the following variables: (Check .env.example for reference)
   ```bash
   KIBANA_URL=<your-kibana-url>
   KIBANA_API_KEY=<your-kibana-api-key>
   SMTP_USER=<your-email-client>
   SMTP_PASSWORD=<your-smtp-password-or-key>
   KIBANA_URL=<your-kibana-url> 
   ```

## Usage
Run the script with the required arguments:
```bash
python main.py -m <receiver_email> [-u <kibana_url>] [-i <rule_id>] [-s <service_id>] [-t <interval>] [-f <log_file>] [-v]
```

### Command-Line Arguments
| Argument  | Description  | Default  |
|-----------|-------------|----------|
| `-u`, `--url`  | Kibana base URL  | `.env` value |
| `-i`, `--id`  | Rule ID to query data from  | `''` |
| `-s`, `--service`  | Rule ID for service query  | `''` |
| `-m`, `--mail`  | Receiver's email address  | **Required** |
| `-ns`, `--notifyslack`  | Notify Slack Channel  | `''` |
| `-t`, `--time`  | Sleep interval between checks (seconds)  | `300` |
| `-f`, `--file`  | Log file to save output  | `anomaly.log` |
| `-v`, `--verbose`  | Enable verbose mode  | `True` |

### Example Usage

```bash
python main.py -m admin@example.com -t 600 -i 'CPU-THRESHOLD-RULE-ID-HERE-XXX' -s 'SERVICE-RULE-ID-HERE-XXX' -v True
```

This command sends anomaly reports to `admin@example.com`, checks every 600 seconds, and enables verbose logging.

## Logging
Logs are saved to `anomaly.log` (or specified file) and include timestamps.

## Error Handling
- The script handles unexpected errors and retries after the specified interval.
- Error messages are logged to the console and the log file.

## Contributing
Feel free to fork the repository, make enhancements, and submit pull requests.

## License
This project is licensed under the MIT License.