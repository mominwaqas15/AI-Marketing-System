import cv2
import time
import torch
import os
from datetime import datetime
import schedule
from threading import Thread
import ChatServices
import detection
import numpy as np

rtsp_url = "rtsp://admin:Ashton2012@41.222.89.66:560"

model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
complement = ChatServices.ImageDescribe()
base_output_dir = 'Human-Detection-Logs'
os.makedirs(base_output_dir, exist_ok=True)

def detect_humans():
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("Error: Could not open RTSP stream.")
        return
 
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    iteration_dir = os.path.join(base_output_dir, timestamp)
    os.makedirs(iteration_dir, exist_ok=True)

    humans_log_path = os.path.join(iteration_dir, "human_detections.txt")
    humans_log_file = open(humans_log_path, "w")

    frame_count = 0 
    start_time = time.time()
    duration = 10  # Adjust duration for frame capturing

    highest_confidence = 0  # Variable to store the highest confidence
    best_frame = None  # Variable to store the frame with the highest confidence
    best_bbox = None  # To store the bounding box for the highest confidence detection

    while time.time() - start_time < duration:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("Error: Failed to grab frame.")
            time.sleep(1)
            continue

        results = model(frame)

        # Extract detection details: class, confidence, and bounding box
        detections = results.xyxy[0].cpu().numpy()  # xyxy format, confidence, class
        for det in detections:
            xmin, ymin, xmax, ymax, conf, cls = det
            if conf > 0.5 and int(cls) == 0:  # Filter for humans (class 0)
                print(f"Human detected in Frame {frame_count:03d} - Confidence: {conf:.2f}")
                # Check if this is the highest confidence detected so far
                if conf > highest_confidence:
                    highest_confidence = conf
                    best_frame = frame.copy()  
                    best_bbox = (xmin, ymin, xmax, ymax)  

        frame_count += 1

    
    cap.release()

    # Save the frame with the highest confidence (if any detection occurred)
    if best_frame is not None:
        frame_save_path = os.path.join(iteration_dir, "highest_confidence_frame.jpg")
        cv2.imwrite(frame_save_path, best_frame)
        print("save path",frame_save_path)
        complement_response = complement.generate_response(image_path=frame_save_path)
        print("------------------------------complement-----------------------------------\n",complement_response)
        humans_log_file.write(
                    f"Frame {frame_count:03d}: Confidence: {conf:.2f}, "
                    f"BBox: [{xmin:.1f}, {ymin:.1f}, {xmax:.1f}, {ymax:.1f}]\n",
                    #f"complement: {complement_response}"
                )
        detection_model = detection.load_detection_model()
        frame = detection_model(best_frame)
        String = str(frame)
        if String:
            print("Hellooooooooo")
        detect = np.squeeze(frame.render())
        cv2.imshow('YOLO', detect)
        print(f"Saved frame with the highest confidence: {highest_confidence:.2f}")
        print(f"BBox: {best_bbox}")
    else:
        print("No human detections with confidence > 0.5.")
    print(f"Finished detecting humans. Logs saved in: {iteration_dir}")


# Schedule the task to run every 2 minutes
schedule.every(2).minutes.do(detect_humans)

# Function to keep the scheduler running
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler in a separate thread
scheduler_thread = Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

print("Scheduler is running. Press Ctrl+C to exit.")
try:
    while True:
        time.sleep(1)  # Keep the main thread alive
except KeyboardInterrupt:
    print("Exiting program.")