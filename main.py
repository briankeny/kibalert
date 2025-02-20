import os
import sys
import argparse
import time
from dotenv import load_dotenv
from rules import  Rule
from mail import SendMail
from host import Host
from latency import Latency
from slack import Slack

# Command Line Args Error Handling
def error_handler(errmsg):
    """Handle errors and exit the script gracefully."""
    print(f"\tUsage: python {sys.argv[0]} -h for help\n")
    print(f"\t[?] Error: {errmsg}\n")
    sys.exit()

# Command Line Arguments
def argument_handler():
    """Handle command-line arguments."""
    parser = argparse.ArgumentParser(description="Anomaly Monitoring and Notification Script")
    parser.add_argument("-u", "--url", default=os.getenv('KIBANA_URL'), help='Elastic base URL')
    parser.add_argument("-i", "--id", type=str,default=os.getenv('ANOMALY_RULE_ID',''), help='Rule ID to query data from')
    parser.add_argument("-t", "--time", type=int, default=os.getenv('SLEEP_TIME',60), help='Time to sleep')
    parser.add_argument("-l", "--latency", type=int, default=os.getenv('LATENCY_THRESHOLD',1000), help='Check for a given latency value in ms')
    parser.add_argument("-c", "--cpu", type=int, default=os.getenv('CPU_THRESHOLD',99) , help='Check for a given CPU % threshold value ie 80')
    parser.add_argument("-s", "--service", type=str, default=os.getenv('SERVICE_ID',''), help='Rule ID for service to query data from')
    parser.add_argument("-m", "--mail", type=str, required=False,default=os.getenv('EMAIL_RECEIVER',''),help="Receiver's email address")
    parser.add_argument("-ns", "--notifyslack", type=str, required=False,default= os.getenv('SLACK_CHANNEL'), help="Send notification to slack by attaching channel name")
    parser.add_argument("-f", "--file", type=str, default=os.getenv('LOG_FILE','anomaly.log'), help='Log file to save output')
    parser.add_argument("-v", "--verbose", default=os.getenv('VERBOSE',True),action="store_true", help="Enable verbose mode")
    parser.error = error_handler
    return parser.parse_args()

def main(url, rule_id, receiver, verbose, save, savefile,sid,interval,slack_channel,latency,cpu):
    """Monitor anomalies and send notifications."""

    def log_message(message=None, filename=savefile):
        """Log messages to console and optionally save to file."""
        if verbose:
            print(message)
        if save and filename:
            with open(filename, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
  
    log_message("Monitoring started...")
    API_KEY = os.getenv('KIBANA_API_KEY')
    headers = {
            "Authorization": f"ApiKey {API_KEY}",
            "kbn-xsrf": "true",
            "Content-Type": "application/json",
    }
    while True:
        try:           
            # Send mail notification
            send_mail = SendMail(receiver=receiver, log_message=log_message)
            slack_token = os.getenv("SLACK_TOKEN")
            webhook_url=os.getenv("SLACK_WEBHOOK_URL")

            #Send notification via slack
            slack = Slack (channel=slack_channel,slack_token=slack_token,log_message=log_message,webhook_url=webhook_url)

            # Fetch from rule
            rule = Rule(service_id=sid,kibana_url=url,rule_id=rule_id,log_message=log_message,send_mail=send_mail.send_mail,headers=headers,send_slack=slack.send_notification, slack_channel=slack_channel,send_via_hook=slack.send_via_hook)
            
            # Host CPU Usage
            rule.fetch_host_alerts()
            log_message('\t Fetching Host CPU Data Usage complete...')
            
            # # # Service Latency  
            rule.fetch_service_alerts()
            log_message('\t Fetching Services Latency Check complete...')

            # # Fetch Host Data
            host = Host(kibana_url=url,headers=headers,log_message=log_message,send_mail=send_mail.send_mail,send_via_hook=slack.send_via_hook,send_slack=slack.send_notification,slack_channel=slack_channel,cpu_threshold=cpu)
            host.get_cpu_usage()
            
            log_message('\t Fetching CPU Data complete...')

            #Fetch Latency Data
            latency = Latency(url=url,headers=headers,log_message=log_message,send_mail=send_mail.send_mail,send_slack=slack.send_notification,slack_channel=slack_channel,latency_threshold=latency,send_via_hook=slack.send_via_hook)
            latency.get_latency()
            log_message('\t Fetching Latency Data complete...')

            log_message('\t Sleeping for {} seconds...'.format(interval))
            time.sleep(interval)
        
        except Exception as e:
            log_message(f"Unexpected error: {e}")
            log_message('\t Sleeping for {} seconds...'.format(interval))
            time.sleep(interval)

if __name__ == "__main__":
    load_dotenv()

    args = argument_handler()
    url = args.url
    rule_id = args.id
    receiver = args.mail
    verbose = args.verbose
    savefile = args.file
    latency = args.latency
    cpu = args.cpu
    save = bool(savefile)
    sid = args.service
    slack_channel = args.notifyslack or os.getenv("SLACK_CHANNEL",None)
    interval=int(args.time)
 
    main(url, rule_id, receiver, verbose, save, savefile,sid,interval,slack_channel,latency,cpu)