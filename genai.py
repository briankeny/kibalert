import os
import uuid
import google.generativeai as genai
from base import Base
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

class GeminiAI(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generateAIresponse(self):
        if not self.MODEL_NAME :
            self.log_message('[+] No AI model selected')
            return
        self.log_message('[-] AI response generation started...')   
        content = []

        if self.AI_PROMPT:
            content.append(self.AI_PROMPT)

        # Append file content as text
        for file_path in [self.USER_LOG_FILE, self.APP_LOG_FILE]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    content.append(file_content)
            except FileNotFoundError:
                print(f"File not found: {file_path}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        try:
            if len(content) > 0:
                model = genai.GenerativeModel(self.MODEL_NAME, system_instruction=self.AI_CONTEXT, safety_settings=None)
                response = model.generate_content(content, stream=True)
                response.resolve()
                report_name = f"report{uuid.uuid4()}.md"
                self.GENERATED_FILES.append(report_name)
                with open(report_name, "w", encoding="utf-8") as f:
                    f.write(response.text)
                    self.log_message('AI response report has been saved to ' + report_name)
                self.full_notify(subject='AI Analysis',message=report_name,file_path=report_name)
                self.log_message('[+] AI response generation complete ...')
                return response
            else:
                self.log_message('[+] Skipping, no content found...')
                return
        except Exception as e:
            self.log_message(f'[-] AI response generation failed: {e}')
            return