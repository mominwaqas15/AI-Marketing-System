import os
import cv2
import time
import httpx
import uvicorn
import asyncio
import schedule
from threading import Thread, Lock, Timer
from ChatServices import Model
from dotenv import load_dotenv
from helper import generate_qr_code
from fastapi.responses import JSONResponse
from DetectionModels import HumanDetection
from fastapi.responses import HTMLResponse
from WhatsappService import WhatsAppService
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks, Request
from html_generator import generate_qr_code_page
from twilio.twiml.messaging_response import MessagingResponse
import sms
import random
from asyncio import Queue
gpt = Model()

load_dotenv()
whatsapp_message_queue = Queue()
whatsapp_service = WhatsAppService()

WEBHOOK_URL = "https://webhook.site/abaccc7d-386f-4f55-83eb-581e8e031838"

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

RTSP_URL = "rtsp://admin:Ashton2012@41.222.89.66:560"
OUTPUT_DIR = "Human-Detection-Logs"
ROI_COORDS = (400, 650, 2750, 2900)  # Specify Region Of Interest coordinates

# Global variables
sessiontoken = None
bestframe = None
complement_queue = []
lock = Lock()  # Lock for thread-safe global variable access

app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

# Initialize detection and chat model
detector = HumanDetection(RTSP_URL, OUTPUT_DIR, ROI_COORDS)
chat_model = Model()

# Global variable to track ongoing chat sessions
active_chat_sessions = {}

def clean_up_logs_and_frames():
    """
    Deletes old frames and logs to maintain memory efficiency.
    """
    logs = os.listdir(OUTPUT_DIR)
    if len(logs) > 50:
        for log in logs[:len(logs) - 50]:
            log_path = os.path.join(OUTPUT_DIR, log)
            if os.path.isfile(log_path):
                os.remove(log_path)

def detect_human_and_gesture():
    global sessiontoken, bestframe, complement_queue

    print("Starting human detection...")
    detection_success, best_frame, frame_path = detector.detect_humans()

    new_session_token = chat_model.generate_token()
    sessiontoken = new_session_token

    print(f"Session Token Initialized: {sessiontoken}")

    with lock:
        if detection_success:
            active_chat_sessions[sessiontoken] = {
                "frame_path": frame_path,
                "timestamp": time.time(),
                "is_placeholder": False,
            }
            if detector.process_frame_for_gesture(best_frame):
                bestframe = best_frame

                # Initialize complement queue as a generator
                complement_generator = chat_model.image_description(image_path=frame_path, token=sessiontoken)

                # Store complements in a list for the session and yield as they are generated
                active_chat_sessions[sessiontoken]["complements"] = []
                for complement in complement_generator:
                    active_chat_sessions[sessiontoken]["complements"].append(complement)
                    print(f"Generated complement: {complement}")
            else:
                print("Gesture detected but no valid complements generated.")
        else:
            active_chat_sessions[sessiontoken] = {
                "frame_path": None,
                "timestamp": time.time(),
                "is_placeholder": True,
            }
            bestframe = None


async def whatsapp_worker():
    while True:
        to_number, message = await whatsapp_message_queue.get()
        try:
            # Retrieve session details for this user
            session_data = active_chat_sessions.get(to_number, {})
            complements = session_data.get("complements", [])

            # Personalize the message with a complement
            personalized_message = message
            if complements:
                personalized_message += f"\n\nHere's something for you: {random.choice(complements)}"

            await sms.send_whatsapp_message(to_number, personalized_message)
        except Exception as e:
            print(f"Failed to send WhatsApp message to {to_number}: {e}")
        finally:
            whatsapp_message_queue.task_done()


def schedule_task():
    """
    Schedule the human detection task every 20 seconds.
    """
    schedule.every(10).seconds.do(detect_human_and_gesture)
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.on_event("startup")
async def start_scheduler():
    """
    Start the scheduler thread when the FastAPI server starts.
    """
    asyncio.create_task(whatsapp_worker())
    print("WhatsApp worker started.")
    scheduler_thread = Thread(target=schedule_task, daemon=True)
    scheduler_thread.start()
    print("Scheduler started.")

    # Use asyncio.create_task instead of asyncio.run to avoid event loop issues
    asyncio.create_task(start_detection(BackgroundTasks()))

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    from_number = form.get("From")
    body = form.get("Body")

    gpt.initialize_chat_history(from_number)
    session_data = gpt.chat_sessions[from_number]

    # Add a complement to the context if available
    complements = session_data.get("complements", [])
    if complements:
        body += f"\n\nFYI: Here's something you might like: {random.choice(complements)}"

    gpt_response = gpt.get_response(user_input=body, phone_number=from_number)
    await whatsapp_message_queue.put((from_number, gpt_response))

    response = MessagingResponse()
    return HTMLResponse(content=str(response), status_code=200)

@app.post("/start-detection")
async def start_detection(background_tasks: BackgroundTasks):
    """
    Endpoint to start human and gesture detection in the background.
    """
    background_tasks.add_task(detect_human_and_gesture)
    return {"message": "Human detection started in the background."}

@app.get("/")
async def root():
    """
    Default page shown when no human is detected.
    """
    return HTMLResponse(content="<html><body><h1>Welcome to Ashton Media!</h1></body></html>")

@app.get("/chat/{session_token}")
async def chat(session_token: str, user_input: str):
    """
    Endpoint for user chat interaction after a gesture is detected. 
    """
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})
    try:
        response = chat_model.get_response(user_input, session_token)
        return {"message": response}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error during chat: {str(e)}"})

@app.get("/show-qr")
async def show_qr_page():
    global sessiontoken, bestframe

    with lock:
        if not sessiontoken:
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        if sessiontoken not in active_chat_sessions:
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        session_data = active_chat_sessions[sessiontoken]

        # Check if complements are available
        complements = session_data.get("complements", [])
        if not complements:
            current_complement = "Welcome to Ashton Media!"
        else:
            # Fetch the next complement (or rotate through complements)
            current_complement = complements.pop(0)
            complements.append(current_complement)  # Rotate complement for reuse

        # Generate WhatsApp QR code
        whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'
        qr_code_path = generate_qr_code(whatsapp_link, sessiontoken)

        # Generate HTML response with QR code and complement
        html_content = generate_qr_code_page(
            complement=current_complement,
            qr_code_path=os.path.basename(qr_code_path),
        )

    return HTMLResponse(content=html_content)


@app.get("/test-qr")
async def test_whatsapp_qr_code():
    """
    Generate a QR code for sending a WhatsApp message.
    """
    

    # Generate WhatsApp link with pre-filled message
    whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'

    # Generate QR code for the WhatsApp link
    qr_code_path = generate_qr_code(url=whatsapp_link, session_token="test")

    # HTML content to display the QR code
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WhatsApp QR Code</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                text-align: center;
            }}
            img {{
                max-width: 300px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Scan the QR Code to Message on WhatsApp</h1>
            <img src="/static/{qr_code_path}" alt="WhatsApp QR Code">
            <p>Or click the link below:</p>
            <a href="{whatsapp_link}" target="_blank">{whatsapp_link}</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)



if __name__ == "__main__":
    uvicorn.run("init:app", host=HOST, port=PORT, reload=True)