import logging
import openai

class OpenAIApiException(Exception):
    pass

class OpenAIApi:
    def __init__(self, api_key, api_base):
        openai.api_key = api_key
        if api_base != "":
            openai.api_base = api_base

    def generate_text(self, script, content):
        try:
            logging.info("Text Generation Started")
            reply = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": script},
                    {"role": "user", "content": content},
                ]
            )
            logging.debug(f"Script reply {reply}")

            if 'choices' not in reply:
                logging.error("Script Generation Failed: 'choices' not in reply")
                return None

            response = reply['choices'][0]['message']['content']

            if response is None or len(response) < 5:
                raise ValueError(f"Response is empty \"{response}\"")
            
            logging.debug(f"Open api responce: {response}")
            response = response.replace("\n\n","\n")
            response = response.split("\n")
            logging.info("Text Generation Finished")

            return response
        except Exception as e:
            logging.error(f"Error occurred in chat_gen: {e}")
            raise OpenAIApiException("OpenAI API Error.") from e