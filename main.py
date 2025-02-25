from datetime import datetime
import os
import sys
import argparse
import time
from dotenv import load_dotenv
from rules import  Rule
from metrics import Metrics
from monitor import Monitor
from elasticlogs import ElasticLogs
from genai import GeminiAI
from deepseek import DeepSeek
from gptai import GptAI
from base import Base

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
    parser.add_argument("-i", "--id", type=str, default=os.getenv('HOSTS_RULE_IDS',None), help='Rule ID to query data from')
    parser.add_argument("-t", "--time", type=int, default=int(os.getenv('SLEEP_TIME', 60)), help='Time to sleep')
    parser.add_argument("-l", "--latency", type=int, default=int(os.getenv('LATENCY_THRESHOLD', 1000)), help='Latency threshold in ms')
    parser.add_argument("-nl", "--notifylimit", type=int, default=int(os.getenv('NOTIFY_LIMIT', 3)), help='Number of notifications per batch')
    parser.add_argument("-c", "--cpu", type=int, default=int(os.getenv('CPU_THRESHOLD', 99)), help='CPU usage threshold in %')
    parser.add_argument("-s", "--service", type=str, default=os.getenv('SERVICE_RULE_IDS',None), help='Service ID for queries')
    parser.add_argument("-m", "--mail", type=str, default=os.getenv('EMAIL_RECEIVERS',None), help="Receiver's email addressed separated by comma if many")
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

# Remove empty items from list 
def parse_list_remove_blanks(items=None):
    if items:
        items =  items.split(',')
        return list(filter(lambda x: x.strip(), items))

    
def main(url, api_key, slack_token, webhook_url, smtp_server, smtp_port, smtp_user, smtp_password, receiver,
         slack_channel, sleep_time, notify_limit, hits_size, log_file, save, verbose, user_log_file,
         latency_threshold, cpu_threshold, rule_id, SERVICE_RULE_IDS):
    """Monitor anomalies and send notifications."""
    if verbose:
        print("Kibalert monitoring started...")
    okay_status = True
    while okay_status:
        try:
            #If no api key is provided, exit
            if not api_key:
                if verbose:
                    print('\t[!] No API key provided. Exiting...')
                break
            
            if receiver:
                receiver = parse_list_remove_blanks(receiver)
            if SERVICE_RULE_IDS:
                SERVICE_RULE_IDS = parse_list_remove_blanks(SERVICE_RULE_IDS)
            if rule_id:
                rule_id = parse_list_remove_blanks(rule_id)
            
            # Read schedule from .env and split into a list
            ai_run_schedules= parse_list_remove_blanks(os.getenv("AI_RUN_SCHEDULES", "00:00,12:00"))
            last_run_file= "last_run.json"
        
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
            'SERVICE_RULE_IDS': SERVICE_RULE_IDS,
            'ai_prompt' : 'Analyse the data and provide insights and resources like links to learn more or address the issues. Generate a detailed report to include findings, actions and reccommendations',
            'ai_model':os.getenv('AI_MODEL',None),
            'ai_context' : os.getenv('AI_CONTEXT',''),
            'deep_seek_key' : os.getenv('DEEPSEEK_API_KEY',None),
            'deep_seek_url' :os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions'),
            'deep_seek_model': os.getenv('DEEPSEEK_API_MODEL','deepseek-model'),
            'openai_model': os.getenv('GPT_MODEL_NAME', 'gpt-3.5-turbo'),
            'openai_api_key' :os.getenv('GPT_API_KEY',None),
            'ai_run_schedules':ai_run_schedules,
            'last_run_file':last_run_file
            }
                        
            # Config
            base  = Base(**base_config)
            # Fetch from rule
            rule = Rule(**base_config)
            rule.fetch_host_alerts()   # Host CPU Usage
            rule.fetch_service_alerts() # Service Latency  
                       
            # Fetch Host and Latency Metrics
            metrics = Metrics(**base_config)
            metrics.get_latency()  # Fetch and process latency data
            metrics.get_cpu_usage() # Fetch and process CPU usage data
            
            # Check Downtime
            monitor = Monitor(**base_config)
            monitor.check_host_downtime()
            monitor.check_service_downtime()
            
            # Collect Logs
            logs = ElasticLogs(**base_config)
            logs.fetch_logs() 
                      
            
            if base.run_ai_now():
                # Gemini AI
                ai = GeminiAI(**base_config)
                ai.generateAIresponse()

                # Deep Seek
                deepseek = DeepSeek(**base_config)
                deepseek.generateReport()

                # OpenAI GPT
                gpt = GptAI(**base_config)
                gpt.promptGPT()
                
                # Update next run time 
                (last_run_tracker,start_time)  = base.run_ai_now()
                last_run_tracker[start_time]['last_run'] = str(datetime.now())
                base.save_last_run(last_run_tracker)

                # Cleanup old log and report files
                base.clean_up_files()

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
        api_key=os.getenv("KIBANA_API_KEY",None),
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
        SERVICE_RULE_IDS=args.service
    )