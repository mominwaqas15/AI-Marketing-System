import uuid
from openai import OpenAI
import datetime
import time
import os
from helper import Helper
from dotenv import load_dotenv
load_dotenv()

class Model:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chat_sessions = {}  # Dictionary to store chat histories against tokens
        self.system_prompt = {"role": "system", "content": "You are a chatbot for Ashton Company."}

    def generate_token(self):
        """Generate a unique session token."""
        return str(uuid.uuid4())

    def initialize_chat_history(self, token): 
        """Initialize chat history for a specific session."""
        self.chat_sessions[token] = [self.system_prompt]

    def get_response(self, user_input, token):
        """Generate a response to the user's input for a specific session."""
        if token not in self.chat_sessions:
            raise ValueError("Invalid session token. Please initialize a new session.")

        # Add user input to the session's chat history
        self.chat_sessions[token].append({"role": "user", "content": user_input})

        # Generate response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=self.chat_sessions[token], 
            stream=True,
        )

        # Stream and collect the AI's response
        response_str = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                response_str += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
                time.sleep(0.02)

        # Add the AI's response to the session's chat history
        self.chat_sessions[token].append({"role": "assistant", "content": response_str})
        print()  # Newline after streaming response
        return response_str

    def image_description(self, image_path, token):
        """Generate a description based on an image for a specific session."""
        if token not in self.chat_sessions:
            raise ValueError("Invalid session token. Please initialize a new session.")

        PROMPT = "Your task is to complement the person in the image based on their outfit or something relevant to them. Don't assume anything, give response according to the image provided."
        base64_image = Helper.encode_image(image_path)

        history = self.chat_sessions[token] + [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Given the following base64-encoded image + {PROMPT}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=5000,
            messages=history,
            stream=True,
        )

        response_str = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                response_str += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
                time.sleep(0.02)

        # Add AI response to chat history
        self.chat_sessions[token].append({"role": "assistant", "content": response_str})
        print()  # Newline after response
        return response_str


# Main interactive loop
if __name__ == "__main__":
    model = Model()

    print("Welcome to Ashton Chatbot. Type 'exit' to end the chat.")
    session_token = model.generate_token()
    model.initialize_chat_history(session_token)
    print(f"Your session token: {session_token}")
    
    flag = False
    while True:
        if flag == False:
            model.image_description('hi_gesture.jpg', session_token)
            flag = True
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        elif user_input.startswith("image:"):
            # Handle image input (e.g., "image:/path/to/image.jpg")
            image_path = user_input.split("image:")[1].strip()
            try:
                model.image_description(image_path, session_token)
            except Exception as e:
                print(f"Error processing image: {e}")
        else:
            try:
                model.get_response(user_input, session_token)
            except Exception as e:
                print(f"Error: {e}")