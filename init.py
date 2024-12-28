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

    with lock:
        if detection_success:
            sessiontoken = new_session_token
            active_chat_sessions[sessiontoken] = {
                "frame_path": frame_path,
                "timestamp": time.time(),
                "is_placeholder": False,
            }
            if detector.process_frame_for_gesture(best_frame):
                bestframe = best_frame

                # Initialize complement queue as a generator
                complement_queue = chat_model.image_description(image_path=frame_path, token=sessiontoken)
            else:
                print("Gesture detected but no valid complements generated.")
        else:
            if sessiontoken is None:
                sessiontoken = new_session_token
                active_chat_sessions[sessiontoken] = {
                    "frame_path": None,
                    "timestamp": time.time(),
                    "is_placeholder": True,
                }
                bestframe = None


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
    global sessiontoken, bestframe, complement_queue

    with lock:
        if not sessiontoken or sessiontoken not in active_chat_sessions:
            return JSONResponse(status_code=404, content={"message": "No active session or session expired."})

        session_data = active_chat_sessions[sessiontoken]
        if bestframe is None:
            return JSONResponse(status_code=404, content={"message": "No valid complement available."})

        try:
            # Fetch the next complement
            current_complement = next(complement_queue)
        except StopIteration:
            return JSONResponse(status_code=404, content={"message": "No more complements available."})

        whatsapp_link = f'https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I\'m%20interested%20in%20chatting.'
        qr_code_path = generate_qr_code(whatsapp_link, sessiontoken)

        html_content = generate_qr_code_page(
            complement=current_complement,
            qr_code_path=os.path.basename(qr_code_path),
        )

    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("init:app", host=HOST, port=PORT, reload=True)