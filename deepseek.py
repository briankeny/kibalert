import os
import uuid
import requests
from dotenv import load_dotenv
from base import Base

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions")

class DeepSeek(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def promptDeepSeek(self, prompt, model="deepseek-model", temperature=0.7, top_p=1.0, frequency_penalty=0, presence_penalty=0, max_tokens=1000):
        """
        Sends a prompt to the DeepSeek API and returns the response.
        """
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "max_tokens": max_tokens
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_message(f'[-] DeepSeek API request failed: {e}')
            return None

    def generateReport(self):
        """
        Generates a report using the DeepSeek model.
        """
        if not self.MODEL_NAME or DEEPSEEK_API_KEY is None:
            if self.VERBOSE:
                self.log_message('[+] No AI model selected')
            return
        
        if self.VERBOSE:
            self.log_message('[-] DeepSeekAI generation started...')
        content = []

        # Append AI prompt
        if self.AI_PROMPT:
            content.append(self.AI_PROMPT)

        # Append file content
        for file_path in [self.USER_LOG_FILE, self.APP_LOG_FILE]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    content.append(file_content)
            except FileNotFoundError:
                if self.VERBOSE:
                    self.log_message(f"File not found: {file_path}")
            except Exception as e:
                if self.VERBOSE:
                    self.log_message(f"Error reading file {file_path}: {e}")

        if len(content) > 0:
            try:
                # Combine all content into a single prompt
                combined_prompt = "\n".join(content)
                response = self.promptDeepSeek(
                    prompt=combined_prompt,
                    model=self.MODEL_NAME,
                    temperature=0.7,
                    max_tokens=1000
                )

                if response:
                    # Extract the generated text from the response
                    generated_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    report_name = f"report{uuid.uuid4()}.md"

                    # Save the report
                    with open(report_name, "w", encoding="utf-8") as f:
                        f.write(generated_text)
                        if self.VERBOSE:
                            self.log_message('DeepSeekAI report has been saved to ' + report_name)

                    # Notify about the report
                    self.full_notify(subject='AI Analysis', message=report_name, file_path=report_name)
                    if self.VERBOSE:
                        self.log_message('[+] DeepSeekAI generation complete ...')
                    return generated_text
                else:
                    if self.VERBOSE:
                        self.log_message('[+] No response received from DeepSeek API')
                    return None
            except Exception as e:
                if self.VERBOSE:
                    self.log_message(f'[-] DeepSeekAI generation failed: {e}')
                return None
        else:
            if self.VERBOSE:
                self.log_message('[+] Skipping, no content found...')
            return None