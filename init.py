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
from helper import generate_qr_code, generate_QR
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
from fastapi import FastAPI, BackgroundTasks, Request, UploadFile, File
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from DetectionModels import HumanDetection
import types
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


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
WHATSAPP_PHONE_NUMBER_LINK = os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")

RTSP_URL = "rtsp://admin:Ashton2012@41.222.89.66:560"
OUTPUT_DIR = "Human-Detection-Logs"
ROI_COORDS = (400, 650, 2750, 2900)  # Specify Region Of Interest coordinates   

# Load the gesture recognition model
base_options = python.BaseOptions(model_asset_path='gesture_recognizer.task')
gesture_options = vision.GestureRecognizerOptions(base_options=base_options)
gesture_recognizer = vision.GestureRecognizer.create_from_options(gesture_options)

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
    if len(logs) > 30:
        for log in logs[:len(logs) - 50]:
            log_path = os.path.join(OUTPUT_DIR, log)
            if os.path.isfile(log_path):
                os.remove(log_path)

def detect_human_and_gesture():
    """
    Detects humans and gestures, initializes or updates session data,
    and generates or assigns complements for the session.
    """
    global sessiontoken, bestframe

    print("Starting human detection...")
    detection_success, best_frame, frame_path = detector.detect_humans()

    # Generate a new session token
    new_session_token = chat_model.generate_token()
    sessiontoken = new_session_token

    print(f"Session Token Initialized: {sessiontoken}")

    with lock:
        # Initialize the session in active_chat_sessions if it doesn't exist
        if sessiontoken not in active_chat_sessions:
            active_chat_sessions[sessiontoken] = {
            "frame_path": None,
            "timestamp": time.time(),
            "is_placeholder": True,
            "complements": ["Welcome to Ashton Media! We hope you have a great experience!"],  # Default complement
        }
        if detection_success:
            # Update session with detection details
            active_chat_sessions[sessiontoken].update({
                "frame_path": frame_path,
                "timestamp": time.time(),
                "is_placeholder": False,
            })

            # Generate complements if best_frame is not None
            if best_frame is not None:
                try:
                    complement_generator = chat_model.image_description(image_path=frame_path, token=sessiontoken)
                    complements = list(complement_generator)  # Consume the generator into a list
                    active_chat_sessions[sessiontoken]["complements"] = complements
                    print(f"Complements generated for session {sessiontoken}: {complements}")
                except Exception as e:
                    print(f"Error generating complements for best frame: {e}")

            # Save the frame to a temporary file for gesture recognition
            temp_frame_path = os.path.join(OUTPUT_DIR, "temp_frame.jpg")
            cv2.imwrite(temp_frame_path, best_frame)

            # Generate complements if a valid gesture is detected
            gesture_results = detector.process_frame_for_gesture(temp_frame_path)
            if gesture_results:  # Check if gestures are detected
                bestframe = best_frame
                try:
                    complement_generator = chat_model.image_description(image_path=frame_path, token=sessiontoken)
                    complements = list(complement_generator)  # Consume the generator into a list
                    active_chat_sessions[sessiontoken]["complements"] = complements
                    print(f"Gesture-based complements generated for session {sessiontoken}: {complements}")
                except Exception as e:
                    print(f"Error generating gesture-based complements: {e}")
            else:
                print("No valid gestures detected in the frame.")
        else:
            best_frame = None
            print("No human detected. Initializing session with default complements.")

        # Log the current session details
        print(f"Session {sessiontoken} details: {active_chat_sessions[sessiontoken]}")



async def whatsapp_worker():
    while True:
        to_number, message = await whatsapp_message_queue.get()
        try:
            # Send the message as it is (already contextualized by get_response)
            await sms.send_whatsapp_message(to_number, message)
        except Exception as e:
            print(f"Failed to send WhatsApp message to {to_number}: {e}")
        finally:
            whatsapp_message_queue.task_done()

async def detection_task():
    while True:
        detect_human_and_gesture()
        await asyncio.sleep(.5)

@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(whatsapp_worker())
    asyncio.create_task(detection_task())
    print("Schedulers started.")

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    from_number = form.get("From")
    body = form.get("Body")

    # Initialize or retrieve chat history
    gpt.initialize_chat_history(from_number)

    # Generate response
    gpt_response = gpt.get_response(user_input=body, phone_number=from_number)

    # Retrieve complements for this session
    complements = gpt.chat_sessions[from_number].get("complements", [])

    # Queue the response for WhatsApp with complements
    await sms.send_whatsapp_message(to_number=from_number, message=gpt_response, complements=complements)

    # Respond to Twilio
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
    Endpoint for user chat interaction after a gesture is detected .
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
    whatsapp_link = f'https://wa.me/{WHATSAPP_PHONE_NUMBER_LINK}?text=Hi!%20I\'m%20interested%20in%20chatting.'
    qr_code_path = generate_QR(whatsapp_link)

    with lock:
        if not sessiontoken:
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        if sessiontoken not in active_chat_sessions:
            print("\n\n\nSession not found in active sessions.\n\n\n")
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        # Retrieve session data
        session_data = active_chat_sessions[sessiontoken]

        # Ensure complements are available
        complements = session_data.get("complements", [])
        if isinstance(complements, types.GeneratorType):
            complements = list(complements)  # Consume the generator if it's not already a list
            session_data["complements"] = complements  # Update with the consumed list

        if not complements:
            current_complement = "Welcome to Ashton Media!"
        else:
            current_complement = complements.pop(0)  # Get the first complement
            complements.append(current_complement)  # Rotate for reuse

        # Update complements in the session
        session_data["complements"] = complements

        # Generate HTML response with QR code and complement
        html_content = generate_qr_code_page(
            complement=current_complement,
            qr_code_path=os.path.basename(qr_code_path),
        )

    return HTMLResponse(content=html_content)


@app.post("/test-gesture")
async def test_gesture(image: UploadFile = File(...)):
    """
    Detect gestures in the provided image using the gesture_recognizer.task model.
    """
    try:
        # Read and decode the uploaded image
        contents = await image.read()
        np_image = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

        # Save the frame as a temporary file for gesture detection
        temp_image_path = "temp_input_image.jpg"
        cv2.imwrite(temp_image_path, frame)

        # MediaPipe Gesture Recognition
        try:
            # Create MediaPipe Image from file
            mp_image = mp.Image.create_from_file(temp_image_path)
            recognition_result = gesture_recognizer.recognize(mp_image)

            if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                gestures = [
                    {
                        "gesture": gesture.category_name,
                        "confidence": float(gesture.score)
                    }
                    for gesture in recognition_result.gestures[0]
                ]
            else:
                gestures = []

            return JSONResponse(status_code=200, content={"gestures": gestures})

        except Exception as e:
            return JSONResponse(status_code=500, content={"message": f"Error during gesture detection: {str(e)}"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error processing input image: {str(e)}"})

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