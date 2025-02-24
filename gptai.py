from openai import OpenAI
import uuid
from base import Base


class GptAI(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def promptGPT(self):
        if not self.GPT_API_KEY:
            if self.VERBOSE:
                self.log_message('[+] No OpenAI API key provided')
            return
        
        client = OpenAI(api_key=self.GPT_API_KEY)  
        
        self.log_message('[-] OpenAI generation started...')   
        content = []
        
        if self.AI_CONTEXT:
            content.append({"role": "system", "content": self.AI_CONTEXT})

        if self.AI_PROMPT:
            content.append({"role": "user", "content": self.AI_PROMPT})

        # Append file content as text
        for file_path in [self.USER_LOG_FILE, self.APP_LOG_FILE]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if file_content:
                        content.append({"role": "user", "content": file_content})
            except FileNotFoundError:
                self.log_message(f"[-] File not found: {file_path}")
            except Exception as e:
                self.log_message(f"[-] Error reading file {file_path}: {e}")

        if not content:
            self.log_message('[+] Skipping, no content found...')
            return

        try:
            response = client.chat.completions.create(
                model=self.GPT_MODEL_NAME, 
                messages=content,
                temperature=0.7
            )
            
            report_text = response.choices[0].message.content
            report_name = f"report_{uuid.uuid4()}.md"
            with open(report_name, "w", encoding="utf-8") as f:
                f.write(report_text)
            
            if self.VERBOSE:
                self.log_message(f'[+] OpenAI report saved to {report_name}')
            
            self.full_notify(subject='AI Analysis', message=report_name, file_path=report_name)
            self.log_message('[+] OpenAI generation complete ...')

            return response
        except Exception as e:
            self.log_message(f'[-] OpenAI generation failed: {e}')
            return
