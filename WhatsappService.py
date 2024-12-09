from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

class WhatsAppService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_whatsapp_number = os.getenv("WHATSAPP_NUMBER")
        self.to_whatsapp_number = os.getenv("MOMIN_NUMBER")
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_message(self, message: str):
        """
        Send a message via WhatsApp.
        """
        try:
            message_instance = self.client.messages.create(  
                body=message,
                from_=f"whatsapp:{self.from_whatsapp_number}",
                to=f"whatsapp:{self.to_whatsapp_number}",
            )
            return {"status": "success", "sid": message_instance.sid}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def receive_message(self):
        """
        Handle incoming WhatsApp messages (to be configured with a webhook).
        """
        # This method will be implemented with a webhook endpoint in FastAPI.
        pass


if __name__ == "__main__":
    # Initialize WhatsApp Service
    whatsapp_service = WhatsAppService()

    # Replace with a real WhatsApp number in the format +<country_code><phone_number>
    to_number = os.getenv("MOMIN_NUMBER")
    
    # Message to send
    message = "Hello, this is a test message from WhatsAppService!"

    # Send message
    response = whatsapp_service.send_message(message)

    # Print response
    print("Response:", response)