import os
import uuid
# import textwrap
import google.generativeai as genai
# from IPython.display import display, Markdown
# from io import BytesIO
from base import Base
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

class AI(Base):
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
                # Check for attachments:
                # if response and hasattr(response, "parts"):
                #     for part in response.parts:
                #         if hasattr(part, "inline_data") and part.inline_data:
                #             data = part.inline_data.data
                #             mime_type = part.inline_data.mime_type
                #             if mime_type == "application/pdf":
                #                 # Save the PDF:
                #                 rep_name = f"report{uuid.uuid4()}"
                #                 with open(rep_name, "wb") as f:
                #                     f.write(data)
                                
                #                 if self.VERBOSE:
                #                     self.log_message(f"PDF report saved to {rep_name}")
                                
                #                 if self.VERBOSE:
                #                     self.log_message("Sending PDF report as attachment")
                #                 self.full_notify(subject='AI response PDF Analysis', message=rep_name, attachment=rep_name)

                #             elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                #                 # Save the word docx
                #                 rep_name = f"report{uuid.uuid4()}"
                #                 with open(rep_name, "wb") as f:
                #                     f.write(data)
                            
                #                 if self.VERBOSE:
                #                     self.log_message(f"Word report saved to {rep_name}")

                #                 if self.VERBOSE:
                #                     self.log_message("Sending word report as attachment")

                #                 self.full_notify(subject='AI response WORD Analysis', message=rep_name, attachment=rep_name)

                #             else:
                #                 if self.VERBOSE:
                #                     self.log_message(f"Attachment found, mime type: {mime_type}, but not handled")

                #         elif hasattr(part, "text"):
                #             if self.SAVE:
                #                 self.full_notify(subject='AI response text Analysis', message=part.text)
                #         else:
                #             self.brief_notify('AI could not find much', part.text)
                #             if self.VERBOSE:
                #                 self.log_message("Response part without inline data or text.")
                # else:
                #     plain_text =  response.text
                #     self.full_notify(subject='AI Analysis', message=plain_text)
                
                report_name = f"report{uuid.uuid4()}.md"
                with open(report_name, "w", encoding="utf-8") as f:
                    f.write(response.text)
                    if self.VERBOSE:
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
        
    # def to_markdown(self, text):
    #     text = text.replace('•', '  *')
    #     return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


