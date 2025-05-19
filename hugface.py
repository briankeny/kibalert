import re
import uuid
from huggingface_hub import InferenceClient
from  base import Base

class HuggingFaceAI(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def preprocess_logs(self, log_file):
        """
        Extracts and categorizes critical logs for better AI analysis.
        """
        error_patterns = {
            "SSL Errors": r"(OpenSSL error|SSL routines::wrong version number)",
            "PHP Errors": r"(PHP Fatal error|PHP Warning|Undefined variable|Attempt to read property on null)",
            "Kubernetes Errors": r"(Evicted|OOMKilled|CrashLoopBackOff|Pod is in failed state)",
            "Network Issues": r"(connection refused|timeout|failed to connect|network unreachable)"
        }

        categorized_logs = {key: [] for key in error_patterns}

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    for category, pattern in error_patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            categorized_logs[category].append(line.strip())

            formatted_logs = []
            for category, logs in categorized_logs.items():
                if logs:
                    formatted_logs.append(f"## {category}\n- " + "\n- ".join(logs))

            return "\n".join(formatted_logs)

        except FileNotFoundError:
            if self.VERBOSE:
                self.log_message(f"[ERROR] Log file not found: {log_file}")
            return "No logs found."
        except Exception as e:
            if self.VERBOSE:
                self.log_message(f"[ERROR] Failed to process logs: {e}")
            return "Error processing logs."

    def prompt_hug_face_ai(self):
        try:
            if not self.HF_API_KEY or not self.HF_PROVIDER or not self.HF_MODEL:
                if self.VERBOSE:
                    self.log_message('[+] Hug Face AI response generation skipped ...')
                return
            if self.VERBOSE:
                self.log_message('[-] Hug Face AI response generation started...')
            client = InferenceClient(
                provider=self.HF_PROVIDER,
                model=self.HF_MODEL,
                api_key=self.HF_API_KEY,
            )

            log_summary = self.summarize_logs(self.APP_LOG_FILE)
            error_report = self.preprocess_logs(self.USER_LOG_FILE)

            prompt = [
                {
                    "role": "system",
                    "content": f"{self.AI_CONTEXT} { self.HF_TEMPLATE.strip() if self.HF_TEMPLATE else ''}"
                },
                {
                    "role": "user",
                    "content": f"""
                    Here is a summarized log file:
                    ```log
                    {log_summary}
                    ```
                    Key errors detected:
                    ```log
                    {error_report}
                    ```
                     {self.AI_PROMPT}
                    """
                }
            ]

            resp = client.chat_completion(prompt, max_tokens=self.HF_MAX_TOKENS, temperature=self.AI_TEMPERATURE)
            message = resp.choices[0].message.content
            if not message:
                if self.VERBOSE:
                    self.log_message('[+] Hug Face AI response generation skipped ...')
                return
            report_name = f"report{uuid.uuid4()}.md"
            self.GENERATED_FILES.append(report_name)
            with open(report_name, "w", encoding="utf-8") as f:
                f.write(message)
                if self.VERBOSE:
                    self.log_message('Hug Face AI response report has been saved to ' + report_name)
            self.full_notify(subject='AI Analysis',message=report_name,file_path=report_name)
            if self.VERBOSE:
                self.log_message('[+] Hug Face AI response generation complete ...')
            return message
        except Exception as e:
            if self.VERBOSE:
                self.log_message('Hug Face Ai could not generate the response: ' + str(e))
            return None
