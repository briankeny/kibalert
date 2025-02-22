import os
import sys
import argparse
import time
from dotenv import load_dotenv
from rules import  Rule
from metrics import (Latency,Host)
from monitor import Monitor
from logs import Logs
from genai import AI

# Command Line Args Error Handling
def error_handler(errmsg):
    """Handle errors and exit the script gracefully."""
    print(f"\tUsage: python {sys.argv[0]} -h for help\n")
    print(f"\t[?] Error: {errmsg}\n")
    sys.exit()

def argument_handler():
    """Handle command-line arguments."""
    parser = argparse.ArgumentParser(description="Anomaly Monitoring and Notification Script")
    parser.add_argument("-u", "--url", default=os.getenv('KIBANA_URL'), help='Elastic base URL')
    parser.add_argument("-i", "--id", type=str, default=os.getenv('ANOMALY_RULE_ID', ''), help='Rule ID to query data from')
    parser.add_argument("-t", "--time", type=int, default=int(os.getenv('SLEEP_TIME', 60)), help='Time to sleep')
    parser.add_argument("-l", "--latency", type=int, default=int(os.getenv('LATENCY_THRESHOLD', 1000)), help='Latency threshold in ms')
    parser.add_argument("-nl", "--notifylimit", type=int, default=int(os.getenv('NOTIFY_LIMIT', 3)), help='Number of notifications per batch')
    parser.add_argument("-c", "--cpu", type=int, default=int(os.getenv('CPU_THRESHOLD', 99)), help='CPU usage threshold in %')
    parser.add_argument("-s", "--service", type=str, default=os.getenv('SERVICE_ID', ''), help='Service ID for queries')
    parser.add_argument("-m", "--mail", type=str, default=os.getenv('EMAIL_RECEIVER', ''), help="Receiver's email address")
    parser.add_argument("-ns", "--notifyslack", type=str, default=os.getenv('SLACK_CHANNEL',''), help="Slack channel for notifications")
    parser.add_argument("-st","--slacktoken", type=str, default=os.getenv('SLACK_TOKEN',''), help="Slack token or slack api key for sdk")
    parser.add_argument("-f", "--file", type=str, default=os.getenv('APP_LOG_FILE', 'anomaly.log'), help='Log file')
    parser.add_argument("-v", "--verbose", action="store_true", default=os.getenv('VERBOSE', True), help="Enable verbose mode")
    parser.add_argument("-w", "--webhook", type=str, default=os.getenv('SLACK_WEBHOOK_URL', ''), help="Slack webhook URL")
    parser.add_argument("--smtp_server", type=str, default=os.getenv('SMTP_SERVER', ''), help="SMTP server address")
    parser.add_argument("--smtp_port", type=int, default=int(os.getenv('SMTP_PORT', 587)), help="SMTP port number")
    parser.add_argument("--smtp_user", type=str, default=os.getenv('SMTP_USER', ''), help="SMTP username")
    parser.add_argument("--smtp_password", type=str, default=os.getenv('SMTP_PASSWORD', ''), help="SMTP password")
    parser.add_argument("--userlog", type=str, default=os.getenv('USER_LOG_FILE', 'user_activity.log'), help="User activity log file")
    parser.add_argument("--hits_size", type=int, default=int(os.getenv('HITS_SIZE', 100)), help="Hits size per query")

    return parser.parse_args()

def main(url, api_key, slack_token, webhook_url, smtp_server, smtp_port, smtp_user, smtp_password, receiver,
         slack_channel, sleep_time, notify_limit, hits_size, log_file, save, verbose, user_log_file,
         latency_threshold, cpu_threshold, rule_id, service_id):
    """Monitor anomalies and send notifications."""
    if verbose:
        print("Kibalert monitoring started...")
    while True:
        try:
            # Configure base class params
            base_config = {
            'kibana_url': url,
            'api_key': api_key,
            'slack_token': slack_token,
            'webhook_url': webhook_url,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'receiver': receiver,
            'slack_channel': slack_channel,
            'sleep_time': sleep_time,
            'notify_limit': notify_limit,
            'hits_size': hits_size,
            'log_file': log_file,
            'save': save,
            'verbose': verbose,
            'user_log_file': user_log_file,
            'latency_threshold': latency_threshold,
            'cpu_threshold': cpu_threshold,
            'rule_id': rule_id,
            'service_id': service_id,
            'ai_prompt' : 'Analyse data and provide insights. Generate a pdf or word report',
            'ai_model':os.getenv('AI_MODEL',None),
            'ai_context' : os.getenv('AI_CONTEXT',''),
            }

            # # Fetch from rule
            # rule = Rule(**base_config)
            # # Host CPU Usage
            # rule.fetch_host_alerts()  
            # # Service Latency  
            # rule.fetch_service_alerts()
            # # Fetch Host Data
            # host = Host(**base_config)
            # host.get_cpu_usage()
            # # Fetch Latency Data
            # latency = Latency(**base_config)
            # latency.get_latency()
            
            # # Check Downtime
            # monitor = Monitor(**base_config)
            # monitor.check_host_downtime()
            # monitor.check_service_downtime()
            
            # Collect Logs
            logs = Logs(**base_config)
            logs.fetch_logs() 

            # AI
            ai = AI(**base_config)
            ai.generateAIresponse()

            if verbose:
                print('\t Sleeping for {} seconds...'.format(sleep_time))
            time.sleep(sleep_time)
           
        except Exception as e:
            if verbose:
                print(f"Unexpected error: {e}")
                print('\n\n\t Sleeping for {} seconds...\n'.format(sleep_time))
            time.sleep(sleep_time)

if __name__ == "__main__":
    load_dotenv()

    args = argument_handler()
    main(
        url=args.url,
        api_key=os.getenv("KIBANA_API_KEY", ""),
        slack_token=args.slacktoken,
        webhook_url=args.webhook,
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
        smtp_user=args.smtp_user,
        smtp_password=args.smtp_password,
        receiver=args.mail,
        slack_channel=args.notifyslack,
        sleep_time=args.time,
        notify_limit=args.notifylimit,
        hits_size=args.hits_size,
        log_file=args.file,
        save=bool(args.file),
        verbose=args.verbose,
        user_log_file=args.userlog,
        latency_threshold=args.latency,
        cpu_threshold=args.cpu,
        rule_id=args.id,
        service_id=args.service
    )