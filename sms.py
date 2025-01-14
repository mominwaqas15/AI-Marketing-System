
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

async def send_whatsapp_message(to_number: str, message: str, complements: list = None):
    try:
        # Add complements to the message
        if complements:
            personalized_message = f"{message} Also, a quick note: {' '.join(complements)}"
        else:
            personalized_message = message

        # Ensure both numbers have 'whatsapp:' prefix
        formatted_to_number = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
        formatted_from_number = os.getenv("TWILIO_PHONE_NUMBER")

        print(f"Sending message from {formatted_from_number} to {formatted_to_number}")

        # Send the message
        twilio_client.messages.create(
            from_=formatted_from_number,
            body=personalized_message,
            to=formatted_to_number
        )
        print(f"Message sent successfully.")
    except Exception as e:
        print(f"Error sending message: {e}")


# import asyncio

# # Test the send_whatsapp_message function
# async def test_whatsapp():
#     to_number = "+923224205304"  # Replace with your WhatsApp number
#     message = "Hello from Twilio!"
#     await send_whatsapp_message(to_number, message)

# asyncio.run(test_whatsapp())
