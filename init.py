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

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from DetectionModels import HumanDetection


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
        # Initialize the session in active_chat_sessions
        if sessiontoken not in active_chat_sessions:
            active_chat_sessions[sessiontoken] = {
                "frame_path": None,
                "timestamp": time.time(),
                "is_placeholder": True,
                "complements": [],
            }

        if sessiontoken not in chat_model.chat_sessions:
            chat_model.initialize_chat_history(sessiontoken)            

        if detection_success:
            # Update session with detection details
            active_chat_sessions[sessiontoken].update({
                "frame_path": frame_path,
                "timestamp": time.time(),
                "is_placeholder": False,
            })

            # Save the frame to a temporary file for gesture recognition
            temp_frame_path = os.path.join(OUTPUT_DIR, "temp_frame.jpg")
            cv2.imwrite(temp_frame_path, best_frame)

            if detector.process_frame_for_gesture(temp_frame_path):
                bestframe = best_frame

                # Generate complements for detected human and save them in the session
                complement_generator = chat_model.image_description(image_path=frame_path, token=sessiontoken)
                active_chat_sessions[sessiontoken]["complements"] = complement_generator

                print(f"Complements generated for session {sessiontoken}: {active_chat_sessions[sessiontoken]['complements']}")
            else:
                print("Gesture detected but no valid complements generated.")
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
            # print("\n\n\nno session token\n\n\n")
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        if sessiontoken not in active_chat_sessions:
            print("\n\n\nnot in active sessions\n\n\n")
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        session_data = active_chat_sessions[sessiontoken]

        # Check if complements are available
        complements = list(session_data.get("complements", []))  # Convert to a list
        if not complements:
            current_complement = "Welcome to Ashton Media!"
        else:
            current_complement = complements.pop(0)
            complements.append(current_complement)  # Rotate complement for reuse

        session_data["complements"] = complements                        

        # Generate WhatsApp QR code
        # whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'

        # Generate HTML response with QR code and complement
        html_content = generate_qr_code_page(
            complement=current_complement,
            qr_code_path=os.path.basename(qr_code_path),
        )

    return HTMLResponse(content=html_content)

@app.post("/test-gesture")
async def test_gesture():
    """
    Detect gestures in the best frame from the RTSP stream using both MediaPipe and YOLOv5 models.
    """
    try:
        # Detect humans and retrieve the best frame
        detection_success, best_frame, frame_path = detector.detect_humans()

        if not detection_success or best_frame is None:
            return JSONResponse(status_code=404, content={"message": "No human detected or best frame not available."})

        # Initialize results container
        results = {}

        # MediaPipe Gesture Recognition
        try:
            # Convert the frame to the format required by MediaPipe
            image = mp.Image.create_from_file(frame_path)

            # Run gesture recognition
            recognition_result = gesture_recognizer.recognize(image)

            if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                mediapipe_gestures = [
                    {
                        "gesture": gesture.category_name,
                        "confidence": float(gesture.score)  # Convert to native float for JSON serialization
                    }
                    for gesture in recognition_result.gestures[0]
                ]
            else:
                mediapipe_gestures = []

            results["mediapipe"] = mediapipe_gestures

        except Exception as e:
            results["mediapipe_error"] = str(e)

        # YOLOv5 Gesture Recognition
        try:
            if detector.gesture_detection_model:
                yolo_results = detector.gesture_detection_model(best_frame) 
                yolo_detections = yolo_results.xyxy[0].cpu().numpy()

                yolo_gestures = [
                    {
                        "gesture": detector.gesture_detection_model.names[int(det[5])],
                        "confidence": float(det[4])  # Convert to native float for JSON serialization
                    }
                    for det in yolo_detections
                ]

                results["yolo"] = yolo_gestures
            else:
                results["yolo"] = []

        except Exception as e:
            results["yolo_error"] = str(e)

        return JSONResponse(status_code=200, content={"results": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error processing gesture detection: {str(e)}"})

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