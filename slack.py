import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
import json 

class Slack:
    def __init__(self, channel=None, slack_token=None, log_message=None,webhook_url=None):
        """
        Initialize the Slack notification sender.

        :param channel: The Slack channel to send the notification to (e.g., "#general").
        :param slack_token: The Slack API token (default: loaded from environment variables).
        :param log_message: Optional logging function.
        """
        self.SLACK_TOKEN = slack_token
        self.SLACK_CHANNEL = channel
        self.log_message = log_message
        self.client = WebClient(token=self.SLACK_TOKEN)
        self.WEBHOOK_URL = webhook_url

    def send_notification(self, message, file_path=None):
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