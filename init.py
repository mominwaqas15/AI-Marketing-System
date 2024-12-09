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
# HOST = os.getenv("HOST", "0.0.0.0")     #what abdx wrote
HOST = os.getenv("HOST", "127.0.0.1")     # what momin wrote

RTSP_URL = "rtsp://admin:Ashton2012@41.222.89.66:560"
OUTPUT_DIR = "Human-Detection-Logs" 
ROI_COORDS = (400, 650, 2750, 2900)  # Specify Region Of Interest coordinates

app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

# Initialize detection and chat model
detector = HumanDetection(RTSP_URL, OUTPUT_DIR, ROI_COORDS)
chat_model = Model()

# Global variable to track ongoing chat sessions
active_chat_sessions = {}

# def detect_human_and_gesture():                             # with QR code generation module
#     print("Starting human detection...")

#     # Step 1: Detect human presence
#     detection_success, best_frame, frame_path = detector.detect_humans()

#     detection_success = True            # for simulating True Detection

#     if detection_success:
#         print("Human detected! Generating a complement...")

#         session_token = chat_model.generate_token()
#         chat_model.initialize_chat_history(session_token)

#         # # Step 2: Generate complement to grab attention
#         # try:
#         #     complement = chat_model.image_description(frame_path, session_token)
#         #     print(f"\n\nComplement for the user: {complement}\n\n")
#         #     # send_sms(os.getenv("TWILIO_PHONE_NUMBER"), complement)  # Optional: Send SMS to notify the admin
#         # except Exception as e:
#         #     print(f"Error generating complement: {str(e)}")
#         #     complement = "You look amazing!"

#         # Step 3: Check for gestures
#         print("Checking for gestures...")
#         # gesture_detected = detector.process_frame_for_gesture(best_frame)           # for simulating True Detection

#         gesture_detected = True        # for simulating True Detection

#         if gesture_detected:
#             print("Hi gesture detected! Preparing QR code...")

#             # Step 4: Generate QR code for WhatsApp chat
#             session_token = chat_model.generate_token()
#             chat_model.initialize_chat_history(session_token)
#             active_chat_sessions[session_token] = {
#                 "frame_path": frame_path,
#                 "timestamp": time.time(),
#             }

#             # Create WhatsApp chat link
#             twilio_phone_link = os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")
#             whatsapp_link = f"https://wa.me/{twilio_phone_link}?text=Hi!%20I'm%20interested%20in%20chatting."
#             qr_code_path = generate_qr_code(whatsapp_link, session_token)
#             print(f"QR Code generated at: {qr_code_path}")

#             # Log the URL for debugging
#             print(f"Chat session started. QR Code page available at: http://{HOST}:{PORT}/show-qr/{session_token}")
#         else:
#             print("No valid gesture detected.")
#     else:
#         print("No human detected.")

def detect_human_and_gesture():
    print("Starting human detection...")

    # Step 1: Detect human presence
    detection_success, best_frame, frame_path = detector.detect_humans()

    detection_success = True  # Simulating True Detection

    if detection_success:
        print("Human detected! Generating a complement...")

        session_token = chat_model.generate_token()
        chat_model.initialize_chat_history(session_token)

        active_chat_sessions[session_token] = {
                "frame_path": frame_path,
                "timestamp": time.time(),
            }

        # Step 3: Check for gestures
        print("Checking for gestures...")

        # gesture_detected = detector.process_frame_for_gesture(best_frame)           # for simulating True Detection
        
        gesture_detected = True  # Simulating True Detection

        if gesture_detected:
            print("Hi gesture detected! Preparing QR code...")

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

def schedule_task():
    """
    Schedule the human detection task every 3 minutes.
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
    return {"message": "Human and Gesture Detection API is running!"}

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
async def chat(session_token: str, image_path: str):
    """
    Endpoint for user chat interaction after a gesture is detected.
    """
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})
    try:
        response = chat_model.image_description(image_path, session_token)
        return {"message": response}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error during chat: {str(e)}"})
    
# @app.get("/show-qr/{session_token}")              # Twilio Integration
# async def show_qr_page(session_token: str):
#     """
#     Serve an HTML page with the QR code.
#     """
#     if session_token not in active_chat_sessions:
#         return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})
    
#     # Generate the QR code
#     chat_url = f"http://{HOST}:{PORT}/chat/{session_token}"
#     qr_code_path = generate_qr_code(chat_url, session_token)
    
#     # Serve HTML
#     html_content = f"""
#     <html>
#         <head><title>QR Code for Chat</title></head>
#         <body>
#             <h1>Scan the QR Code to start chatting!</h1>
#             <h2>The Session token is [{session_token}]</h2>
#             <img src="/static/{os.path.basename(qr_code_path)}" alt="QR Code">
#         </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)

@app.get("/show-qr/{session_token}")
async def show_qr_page(session_token: str):
    """
    Serve an HTML page with the QR code.
    """
    if session_token not in active_chat_sessions:
        return JSONResponse(status_code=404, content={"message": "Invalid session token or session expired."})
    
    # Generate the QR code
    whatsapp_link = f"https://wa.me/{os.getenv("TWILIO_PHONE_NUMBER_FOR_LINK")}?text=Hi!%20I'm%20interested%20in%20chatting."
    qr_code_path = generate_qr_code(whatsapp_link, session_token)
    
    # Serve HTML4
    html_content = f"""
    <html>
        <head><title>QR Code for Chat</title></head>
        <body>
            <h1>Scan the QR Code to start chatting on WhatsApp!</h1>
            <img src="/static/{os.path.basename(qr_code_path)}" alt="QR Code">
        </body>
    </html>
    """
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