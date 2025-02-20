from email.mime.base import MIMEBase
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from email import encoders

load_dotenv()

class SendMail:
    def __init__(self, receiver,smtp_server=os.getenv("SMTP_SERVER"),smtp_port=587,smtp_user=os.getenv("SMTP_USER"),smtp_password=os.getenv("SMTP_PASSWORD"),log_message=None):
        # SMTP configuration
        self.SMTP_SERVER = smtp_server
        self.SMTP_PORT = smtp_port
        self.SMTP_USER = smtp_user
        self.SMTP_PASSWORD = smtp_password
        self.EMAIL_RECEIVER = receiver
        self.log_message = log_message

    def send_mail(self, subject, body='',attachment=None):
        """Send email notification via SMTP."""

        if not self.EMAIL_RECEIVER:
            # self.log_message("\t Email receiver is not configured.")
            return

        self.log_message(f"Sending email notification to {self.EMAIL_RECEIVER}")
        msg = MIMEMultipart()
        msg["From"] = self.SMTP_USER
        msg["To"] = self.EMAIL_RECEIVER
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
            
        if self.EMAIL_RECEIVER and self.EMAIL_RECEIVER is not None:
            try:
                with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                    server.starttls()
                    server.login(self.SMTP_USER, self.SMTP_PASSWORD)
                    server.sendmail(self.SMTP_USER, self.EMAIL_RECEIVER, msg.as_string())
                self.log_message(f"Email sent to {self.EMAIL_RECEIVER} successfully.")
            except Exception as e:
                self.log_message(f"Failed to send email: {e}")
                pass