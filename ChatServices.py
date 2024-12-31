import uuid
from openai import OpenAI
import datetime
import time
import os
from helper import Helper
from dotenv import load_dotenv
import random

load_dotenv()

class Model:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chat_sessions = {}  # Maps phone numbers to chat histories
        self.system_prompt = {"role": "system", "content": (
            "You are a chatbot for Ashton Company. "
            "You are an AI assistant designed to help users with any questions or tasks they have. "
            "You should respond in a friendly, professional, and concise manner. "
            "Be proactive in asking clarifying questions if the user's query is unclear, and provide examples when necessary. "
            "If the user asks for technical explanations, provide them in simple terms, avoiding jargon. "
            "You can handle casual conversations and provide suggestions, but always remain respectful and helpful. "
            "If you do not know the answer, admit it honestly and guide the user on how they might find the information. "
            "Your goal is to create a positive, engaging, and informative interaction."
        )}

    def initialize_chat_history(self, phone_number):
        """Initialize chat history for a specific phone number."""
        if phone_number not in self.chat_sessions:
            self.chat_sessions[phone_number] = {
                "history": [self.system_prompt],  # Chat history for this user
                "user_chats": [],  # List to store user messages
                "ai_chats": []     # List to store AI responses
            }

    def generate_token(self):
        """Generate a unique session token."""
        return str(uuid.uuid4())                

    def save_chat(self, phone_number, role, content):
        """Save chats to the session."""
        if phone_number in self.chat_sessions:
            if role == "user":
                self.chat_sessions[phone_number]["user_chats"].append(content)
            elif role == "assistant":
                self.chat_sessions[phone_number]["ai_chats"].append(content)

    def get_response(self, user_input, phone_number):
        """
        Generate a response to the user's input for a specific phone number,
        using complements as part of the conversation context.
        """
        if phone_number not in self.chat_sessions:
            self.initialize_chat_history(phone_number)

        # Add complements to the context if available
        complements = self.chat_sessions[phone_number].get("complements", [])
        if complements:
            context = f"Here's some context about the person your'e talking to: {' '.join(complements)}"
            self.chat_sessions[phone_number]["history"].append({"role": "assistant", "content": context})

        else: 
            context = f"Here's some context about the person your'e talking to: They look nice and bring a nice attitude in the workplace!"            
            self.chat_sessions[phone_number]["history"].append({"role": "assistant", "content": context})
            
        # Add user input to the session's chat history
        self.chat_sessions[phone_number]["history"].append({"role": "user", "content": user_input})
        self.save_chat(phone_number, "user", user_input)

        # Generate response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=self.chat_sessions[phone_number]["history"],
        )

        # Extract the response text from the returned object
        response_str = response.choices[0].message.content

        # Add the AI's response to the session's chat history
        self.chat_sessions[phone_number]["history"].append({"role": "assistant", "content": response_str})
        self.save_chat(phone_number, "assistant", response_str)

        return response_str

    def image_description(self, image_path, token):
        """
        Generate and yield complements based on an image for a specific session.
        Complements are also saved in the session for later use.

        :param image_path: Path to the image.
        :param token: Session token to track chat history.
        :yield: Generated complement as a string.
        """
        if token not in self.chat_sessions:
            raise ValueError("Invalid session token. Please initialize a new session.")
        

        PROMPT_BASE = (
            "Your task is to complement the person in the image based on their outfit or something relevant to them. "
            "Don't assume anything; give a response according to the image provided."
        )

        # Encode the image to base64
        base64_image = Helper.encode_image(image_path)

        # Topics to generate complements
        Things_to_talk_about = ["outfit", "shoes", "attitude in the environment"]

        # Ensure a complements list exists in the session
        if "complements" not in self.chat_sessions[token]:
            self.chat_sessions[token]["complements"] = []

        for topic in Things_to_talk_about:
            # Create a variation of the prompt
            variation_prompt = (
                PROMPT_BASE + f" You can talk about the person's {topic}. Be friendly, inviting, and respectful."
            )

            # Prepare the messages with the prompt and image
            messages = self.chat_sessions[token]["history"] + [
                {
                    "role": "user",
                    "content": f"Given the following base64-encoded image + {variation_prompt}",
                }
            ]

            # Generate a response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.9,  # Higher temperature for more creativity
                max_tokens=500,
                messages=messages,
            )

            # Extract the response text
            response_str = response.choices[0].message.content.strip()

            # Save the response in the session history
            self.chat_sessions[token]["history"].append({"role": "assistant", "content": response_str})

            # Save the complement in the session
            self.chat_sessions[token]["complements"].append(response_str)

            # Yield the complement as it is generated
            yield response_str



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