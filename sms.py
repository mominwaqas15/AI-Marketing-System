
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

def send_sms(to: str, message: str):
    """
    Sends an SMS using Twilio.
    
    :param to: Recipient phone number (e.g., "+1234567890")
    :param message: Message content to be sent
    """
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to
        )
        print(f"Message sent! SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Failed to send message: {str(e)}")
        return False