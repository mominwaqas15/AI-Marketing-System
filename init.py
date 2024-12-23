import os
import cv2
import time
import httpx
import uvicorn
import asyncio
import schedule
from threading import Thread, Lock
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
    global sessiontoken, bestframe
    print("Starting human detection...")

    # Step 1: Detect human presence
    detection_success, best_frame, frame_path = detector.detect_humans()

    # Generate a new session token for fallback
    new_session_token = chat_model.generate_token()

    with lock:
        if detection_success:
            # If a human is detected
            if sessiontoken not in active_chat_sessions or active_chat_sessions[sessiontoken].get("is_placeholder", True):
                # Create a new session only if there is no active session or the active session is a placeholder
                sessiontoken = new_session_token
                print(f"New person detected. Session token set: {sessiontoken}")

                chat_model.initialize_chat_history(sessiontoken)

                active_chat_sessions[sessiontoken] = {
                    "frame_path": frame_path,
                    "timestamp": time.time(),
                    "is_placeholder": False,  # Indicates this is a real session
                }

                bestframe = best_frame
            else:
                print("Person already detected. Keeping the existing session token.")
        else:
            # If no human is detected, do not overwrite the current session token
            if sessiontoken is None:
                sessiontoken = new_session_token
                print("No human detected. Generating placeholder session token.")

                active_chat_sessions[sessiontoken] = {
                    "frame_path": None,
                    "timestamp": time.time(),
                    "is_placeholder": True,  # Indicates this is a placeholder session
                }
                bestframe = None
            else:
                print("No human detected. Keeping the existing valid session token.")




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
    scheduler_thread = Thread(target=schedule_task, daemon=True)
    scheduler_thread.start()
    print("Scheduler started.")

    # Use asyncio.create_task instead of asyncio.run to avoid event loop issues
    asyncio.create_task(start_detection(BackgroundTasks()))


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
        # Ensure a valid session token exists
        if not sessiontoken or sessiontoken not in active_chat_sessions:
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        session_data = active_chat_sessions[sessiontoken]
        is_placeholder = session_data.get("is_placeholder", True)

        if is_placeholder and bestframe is None:
            complement = "Welcome! Feel free to connect with us."  # Placeholder complement
        else:
            # Save the best frame as an image file
            frame_save_path = os.path.join(OUTPUT_DIR, f"{sessiontoken}_frame.jpg")
            if bestframe is not None:
                cv2.imwrite(frame_save_path, bestframe)
                complement = chat_model.image_description(image_path=frame_save_path, token=sessiontoken)
            else:
                complement = "Hello! We detected someone, but there is no frame available."

        # Generate the QR code
        whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'
        qr_code_path = generate_qr_code(whatsapp_link, sessiontoken)

        # Use the HTML generation function
        html_content = generate_qr_code_page(
            complement=complement,
            qr_code_path=os.path.basename(qr_code_path)
        )

    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run("init:app", host=HOST, port=PORT, reload=True)
