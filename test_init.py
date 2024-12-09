from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from threading import Thread
import schedule
import time
import os
from helper import generate_qr_code
import uvicorn
from DetectionModelsTest import HumanDetection
from ChatServices import Model
import qrcode
from fastapi.staticfiles import StaticFiles
from WhatsappService import WhatsAppService
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "127.0.0.1")
RTSP_URL = "rtsp://admin:Ashton2012@41.222.89.66:560"
OUTPUT_DIR = "Human-Detection-Logs"

app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

# Initialize detection and chat models
detector = HumanDetection(OUTPUT_DIR)
chat_model = Model()

# Store active chat sessions
active_chat_sessions = {}

def detect_human_and_gesture():
    print("Starting human detection...")

    detection_success, best_frame, frame_path = detector.detect_humans()
    # detection_success = True  # Simulate successful detection

    if detection_success:
        print("Human detected! Generating a complement...")
        session_token = chat_model.generate_token()
        chat_model.initialize_chat_history(session_token)


        try:
            complement = chat_model.image_description(frame_path, session_token)
            print(f"Complement: {complement}")
        except Exception as e:
            print(f"Error generating complement: {e}")
            complement = "You look amazing!"

        print("Checking for gestures...")

        active_chat_sessions[session_token] = {
                "frame_path": frame_path,
                "timestamp": time.time(),
            }
        
        # gesture_detected = detector.process_frame_for_gesture(best_frame)           # for simulating True Detection
        gesture_detected = True  # Simulate successful gesture detection

        if gesture_detected:
            print("Gesture detected! Generating QR code...")
            whatsapp_link = f"https://wa.me/{os.getenv('TWILIO_PHONE_NUMBER_FOR_LINK')}?text=Hi!%20I'm%20interested%20in%20chatting."
            qr_code_path = generate_qr_code(whatsapp_link, session_token)
            print(f"QR Code generated at: {qr_code_path}")
            print(f"\n\nChat session started. QR Code page available at: http://{HOST}:{PORT}/show-qr/{session_token}\n\n")
        else:
            print("No valid gesture detected.")
    else:
        print("No human detected.")

def schedule_task():
    schedule.every(1).seconds.do(detect_human_and_gesture)
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.on_event("startup")
def start_scheduler():
    scheduler_thread = Thread(target=schedule_task, daemon=True)
    scheduler_thread.start()
    print("Scheduler started.")

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.get("/chat/{session_token}")
async def chat(session_token: str, user_input: str):
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or expired."})
    try:
        response = chat_model.get_response(user_input, session_token)
        return {"message": response}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error during chat: {e}"})

@app.get("/show-qr/{session_token}")
async def show_qr_page(session_token: str):
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or expired."})
    qr_code_path = f"{OUTPUT_DIR}/qr_{session_token}.png"
    html_content = f"""
    <html>
        <head><title>QR Code</title></head>
        <body>
            <h1>Scan to Chat</h1>
            <img src="/static/{os.path.basename(qr_code_path)}" alt="QR Code">
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/start-detection")
async def start_detection(background_tasks: BackgroundTasks):
    background_tasks.add_task(detect_human_and_gesture)
    return {"message": "Detection started in the background"}

if __name__ == "__main__":
    uvicorn.run("test_init:app", host=HOST, port=PORT, reload=True)