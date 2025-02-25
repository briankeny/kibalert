import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
import json 
from email.mime.base import MIMEBase
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from email import encoders
from datetime import datetime, timedelta

load_dotenv()

class Base:
    def __init__(self,kibana_url,api_key,slack_token,webhook_url,smtp_server,smtp_port,smtp_user,smtp_password,receiver,slack_channel, sleep_time,notify_limit, hits_size,log_file,save,verbose,user_log_file,latency_threshold,cpu_threshold,rule_id,SERVICE_RULE_IDS,ai_prompt,ai_model,ai_context,deep_seek_key, deep_seek_url,deep_seek_model,openai_model,openai_api_key,ai_run_schedules,last_run_file):
        self.KIBANA_URL = kibana_url
        self.API_KEY = api_key 
        self.headers = {
            "Authorization": f"ApiKey {api_key}",
            "kbn-xsrf": "true",
            "Content-Type": "application/json",
        }
        self.SLACK_CHANNEL = slack_channel 
        self.SLEEP_TIME = sleep_time 
        self.NOTIFY_LIMIT = notify_limit 
        self.HOSTS_RULE_IDS = rule_id 
        self.SERVICE_RULE_IDS = SERVICE_RULE_IDS 
        self.KIBANA_RULE_URL = f"{kibana_url}/.alerts-*/_search"
        self.LATENCY_THRESHOLD = latency_threshold 
        self.CPU_THRESHOLD = cpu_threshold 
        self.HITS_SIZE = hits_size 
        self.APP_LOG_FILE= log_file 
        self.USER_LOG_FILE = user_log_file
        self.SAVE = save 
        self.VERBOSE = verbose 
        # Slack variables
        self.SLACK_TOKEN = slack_token
        self.client = WebClient(token=self.SLACK_TOKEN)
        self.WEBHOOK_URL = webhook_url
        # SMTP variables
        self.SMTP_SERVER = smtp_server 
        self.SMTP_PORT = smtp_port 
        self.SMTP_USER = smtp_user 
        self.SMTP_PASSWORD = smtp_password 
        self.EMAIL_RECEIVERS = receiver
        # AI variables
        self.AI_PROMPT =  ai_prompt or ''
        self.MODEL_NAME = ai_model
        self.AI_CONTEXT = ai_context 
        
        # Deepseek variables
        self.DEEPSEEK_API_KEY = deep_seek_key or None
        self.DEEPSEEK_API_URL = deep_seek_url or None
        self.DEEPSEEK_API_MODEL = deep_seek_model or  'deepseek-model'

        # OpenAI variables
        self.GPT_MODEL_NAME = openai_model or 'gpt-3.5-turbo'
        self.GPT_API_KEY = openai_api_key or None
        
        #  For cleanup
        self.GENERATED_FILES = []
        
        self.AI_SCHEDULED_RUN_TIMES= ai_run_schedules
        self.LAST_RUN_FILE= last_run_file

    def write_to_log_file(self, log_data, title=''):
        """Write log data to file."""
        if log_data:
            with open(self.USER_LOG_FILE, "a") as file:
                if title:
                    file.write(f"\n{title}\n")
                for log in log_data:
                    file.write(
                        ", ".join(f"{key}: {str(val)}" for key, val in log.items()) + "\n"
                    )

    def send_slack(self, message, file_path=None):
        """
        Send a notification to a Slack channel.

        :param message: The message to send.
        :param file_path: Optional path to a file to upload with the message.
        """
        try:
            
            if not self.SLACK_CHANNEL or self.SLACK_TOKEN:
                return
            
            # Send the message
            self.log_message(f"Sending Slack notification to {self.SLACK_CHANNEL}")
            response = self.client.chat_postMessage(
                channel=self.SLACK_CHANNEL,
                text=message
            )
            self.log_message(f"Slack message sent successfully: {response['ts']}")

            # Attach a file if provided
            if file_path:
                try:
                    self.log_message(f"Attaching file to Slack notification: {file_path}")
                    file_response = self.client.files_upload(
                        channels=self.SLACK_CHANNEL,
                        file=file_path,
                        title=os.path.basename(file_path)
                    )
                    self.log_message(f"File uploaded successfully: {file_response['file']['id']}")
                except SlackApiError as e:
                    self.log_message(f"Failed to upload file: {e.response['error']}")
        except SlackApiError as e:
            self.log_message(f"Failed to send Slack notification: {e.response['error']}")    
            pass

    def send_via_hook(self, message):
        """
        Send a notification to a Slack channel via webhook.

        :param message: The message to send.
        """
        if not self.WEBHOOK_URL:
            # self.log_message("\t Slack webhook URL is not configured.")
            return

        payload = {
            "text": message
        }

        try:
            self.log_message(f"Sending Slack notification via webhook to {self.WEBHOOK_URL}")
            response = requests.post(
                self.WEBHOOK_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                self.log_message("Slack message sent successfully.")
            else:
                self.log_message(f"Failed to send Slack notification: {response.status_code} - {response.text}")
        except Exception as e:
            self.log_message(f"Failed to send Slack notification: {e}")
            pass

    def send_mail(self, subject, body='',attachment=None):
        """Send email notification via SMTP."""

        if not all([self.SMTP_USER, self.SMTP_PASSWORD, self.EMAIL_RECEIVERS]):   
            # self.log_message("\t Email receiver is not configured.")
            return

        self.log_message(f"Sending email notification to {self.EMAIL_RECEIVERS}")
        msg = MIMEMultipart()
        msg["From"] = self.SMTP_USER
        msg["To"] = ", ".join(self.EMAIL_RECEIVERS)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachment:
            try:
                 with open(attachment, "rb") as file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    
                    # Extract the filename from the file path
                    filename = os.path.basename(attachment)
                    
                    # Add the header with the filename
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}"
                    )
                    msg.attach(part)
            except Exception as e:
                self.log_message(f"Failed to attach file: {e}")
                pass
            
        try:
                with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                    server.starttls()
                    server.login(self.SMTP_USER, self.SMTP_PASSWORD)
                    server.sendmail(self.SMTP_USER, self.EMAIL_RECEIVERS, msg.as_string())
                self.log_message(f"Email sent to {self.EMAIL_RECEIVERS} successfully.")
        except Exception as e:
                self.log_message(f"Failed to send email: {e}")
                pass

    def log_message(self,message=None):
        """Log messages to console and save application logs to file."""
        if self.VERBOSE or (isinstance(self.VERBOSE, str) and self.VERBOSE.upper().startswith('T')):
            print(message)
        if self.SAVE:
            with open(self.APP_LOG_FILE, "a") as f:
                f.write(f"{message}\n")

    def brief_notify(self,message):
        """ Send A Brief Notification"""
        if self.SLACK_CHANNEL:
            self.send_slack(message=message)
        else:
            self.send_via_hook(message)
  
    def full_notify(self, subject, message,file_path=None):
        """Send a Full notification via Slack, webhook, or email with attachments"""
        file_path = file_path or self.USER_LOG_FILE
        if file_path:
            if self.SLACK_CHANNEL:
                self.send_slack(message=message, file_path=file_path)
            self.send_mail(subject=subject, body=message, attachment=file_path)
            

    def clean_up_files(self, directory="."):
        """
        Removes specified files from a given directory if they exist.
        :param targets: List of filenames to remove (default: None)
        :param directory: Directory to check (default: current directory ".")
        """
        self.GENERATED_FILES.extend([self.USER_LOG_FILE,self.APP_LOG_FILE]) 
        targets = self.GENERATED_FILES or None
        if targets is None:
            if self.VERBOSE:
                print('[-] No files to cleanup')
            return
        
        for file_name in targets:
            file_path = os.path.join(directory, file_name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    if self.VERBOSE:
                        print(f"[+] Cleanup successful, Removed: {file_path}")
                except Exception as e:
                    if self.VERBOSE:
                        print(f"[-] Failed to remove {file_path}: {e}")
            else:
                if self.VERBOSE:
                    print(f"[-] Cleanup skipped, File not found: {file_path}")
                    
    def load_last_run(self):
        """Load last run timestamps from file, return as dictionary."""
        if os.path.exists(self.LAST_RUN_FILE):
            with open(self.LAST_RUN_FILE, "r") as f:
                data = json.load(f)
                return data
        else:
            with open(self.LAST_RUN_FILE, "w") as f:
                # Initialize the dictionary
                data={}
                for val in self.AI_SCHEDULED_RUN_TIMES:
                    # Get the current time
                    stop_time = datetime.strptime(val, "%H:%M").time()
                    stop_datetime = datetime.combine(datetime.today(), stop_time)
                    # Add 30 minutes
                    new_stop_time = stop_datetime + timedelta(minutes=30)
                    # Extract the new time in "H:M" format
                    data[val] = {'start':val,'stop':new_stop_time.strftime("%H:%M")}
                json.dump(data, f, indent=4)
                return data
                
    def save_last_run(self,data):
        """Save last run to file."""
        if data:
            with open(self.LAST_RUN_FILE, "w") as f:
                json.dump(data, f, indent=4)

    def run_ai_now(self):
        """Check if AI should run based on schedule and 30-minute buffer."""
        # Load the last run times
        last_run_tracker = self.load_last_run()      
        if not last_run_tracker:
            return False
        
        for key,val in last_run_tracker.items():
            # Get current time
            now = datetime.now().replace(second=0, microsecond=0).time()
            # Define time range
            start_time = datetime.strptime(val.get('start','00:00'), "%H:%M").time()
            end_time = datetime.strptime(val.get('stop','00:30'), "%H:%M").time()
            # Check if current time is within the time range
            if start_time <= now <= end_time:
                last_run =  val.get('last_run',None)
                if last_run is None or last_run == '':
                    # Script has not ran
                    return (last_run_tracker,key)           
                else:
                    actual_run_date = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S.%f")
                    datetime_obj = actual_run_date.strftime("%H:%M")
                    datetime_obj = datetime.strptime(datetime_obj, "%H:%M").time()
                    # Check if it already ran in the current timeframe
                    if not(start_time <= datetime_obj <= end_time and actual_run_date.date() == datetime.now().date()):
                        # Script has not ran
                        return (last_run_tracker,key)
        return False
