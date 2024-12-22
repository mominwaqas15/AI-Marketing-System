import os
import cv2
import time
import httpx
import uvicorn
import asyncio
import schedule
from threading import Thread
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

load_dotenv()

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
    global sessiontoken, bestframe
    print("Starting human detection...")

    # Step 1: Detect human presence
    detection_success, best_frame, frame_path = detector.detect_humans()

    if detection_success:
        print("Human detected! Generating a complement...")

        session_token = chat_model.generate_token()
        print(f"Generated session token: {session_token}")

        chat_model.initialize_chat_history(session_token)

        active_chat_sessions[session_token] = {
            "frame_path": frame_path,
            "timestamp": time.time(),
        }

        # Generate complement immediately after human detection
        complement = chat_model.image_description(image_path=frame_path, token=session_token)
        print(f"Generated complement: {complement}")

        # Step 3: Check for gestures
        print("Checking for gestures...")
        gesture_detected = detector.process_frame_for_gesture(best_frame)

        if gesture_detected:
            print("Hi gesture detected! Preparing QR code...")
            sessiontoken = session_token  # Update global variable
            bestframe = best_frame        # Update global variable

            # Generate WhatsApp chat link
            whatsapp_link = f"https://wa.me/{os.getenv('TWILIO_PHONE_NUMBER_FOR_LINK')}?text=Hi!%20I'm%20interested%20in%20chatting."
            qr_code_path = generate_qr_code(whatsapp_link, session_token)

            # Log the URL for debugging
            print(f"Chat session started. QR Code page available at: http://{HOST}:{PORT}/show-qr/{session_token}")

            message = "Hello! Welcome to our chat service. You can now continue the conversation on WhatsApp!"
            response = whatsapp_service.send_message(message)
            print("WhatsApp message sent:", response)
        else:
            print("No valid gesture detected.")
    else:
        print("No human detected.")
        # Ensure no frames or actions are performed
        sessiontoken = None
        bestframe = None


def schedule_task():
    """
    Schedule the human detection task every 20 seconds.
    """
    schedule.every(20).seconds.do(detect_human_and_gesture)
    while True:
        schedule.run_pending()
        time.sleep(1)


@app.on_event("startup")
def start_scheduler():
    """
    Start the scheduler thread when the FastAPI server starts.
    """
    scheduler_thread = Thread(target=schedule_task, daemon=True)
    scheduler_thread.start()
    print("Scheduler started.")


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


@app.get("/get-complement/{session_token}")
async def get_complement(session_token: str, image_path: str):
    """
    Endpoint for generating a complement for an image.
    """
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})
    try:
        response = chat_model.image_description(image_path, session_token)
        return {"message": response}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error during complement generation: {str(e)}"})


@app.get("/show-qr/{session_token}")
async def show_qr_page():
    global sessiontoken, bestframe

    if sessiontoken not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})

    # Save the best frame as an image file
    frame_save_path = os.path.join(OUTPUT_DIR, f"{sessiontoken}_frame.jpg")
    if bestframe is not None:
        cv2.imwrite(frame_save_path, bestframe)
    else:
        return JSONResponse(status_code=500, content={"message": "No frame available to process."})

    # Generate the QR code
    whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'
    qr_code_path = generate_qr_code(whatsapp_link, sessiontoken)

    # Use the HTML generation function
    html_content = generate_qr_code_page(
        complement="Complement already generated earlier.",
        qr_code_path=os.path.basename(qr_code_path)
    )

    return HTMLResponse(content=html_content)


@app.post("/start-detection")
async def start_detection(background_tasks: BackgroundTasks):
    """
    Endpoint to start human and gesture detection in the background.
    """
    background_tasks.add_task(detect_human_and_gesture)
    return {"message": "Human detection started in the background."}

if __name__ == "__main__":
    uvicorn.run("init:app", host=HOST, port=PORT, reload=True)