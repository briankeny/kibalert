import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

class Slack:
    def __init__(self, channel, slack_token=os.getenv("SLACK_TOKEN"), log_message=None):
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

    def send_notification(self, message, file_path=None):
        """
        Send a notification to a Slack channel.

        :param message: The message to send.
        :param file_path: Optional path to a file to upload with the message.
        """
        try:
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
                    self.log_message(f"Attaching file: {file_path}")
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