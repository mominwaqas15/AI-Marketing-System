
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

async def send_whatsapp_message(to_number: str, message: str):
    """
    Send a WhatsApp message using Twilio.
    """
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}",  # Ensure 'whatsapp:' prefix
            body=message,
            to=f"whatsapp:{to_number}"  # Ensure 'whatsapp:' prefix
        )
        print(f"Message sent successfully: {message.sid}")
    except Exception as e:
        print(f"Error sending message: {e}")
