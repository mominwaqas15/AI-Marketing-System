import cv2
import detection 
import time
import torch
import os
from datetime import datetime
import schedule
import ChatServices
import crud
from threading import Thread
import db_connection
import numpy as np
from detection import process_frame
from aimodel import Model
import model

# RTSP Stream URL and ROI coordinates
rtsp_url = "rtsp://admin:Ashton2012@41.222.89.66:560"
xmin, ymin, xmax, ymax = 400, 650, 2600, 2500  # Specify Region Of Interest coordinates

# Load the YOLO model

complement = ChatServices.ImageDescribe()
yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
base_output_dir = 'Human-Detection-Logs'


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
    duration = 3  # Duration to run detection

    highest_confidence = 0  # To track highest-confidence detection
    best_frame = None  # Frame with highest-confidence detection
    best_bbox = None  # Bounding box of the highest-confidence detection 

    try:
        while time.time() - start_time < duration:
            ret, frame = cap.read()

            if not ret or frame is None: 
                print("Error: Failed to grab frame.")
                time.sleep(1)
                continue

            # Crop the frame to the ROI
            roi_frame = frame[ymin:ymax, xmin:xmax]

            # Detect objects in the cropped ROI frame
            results = yolo_model(roi_frame)
            detections = results.xyxy[0].cpu().numpy()  # Bounding boxes, confidence, class

            for det in detections:
                det_xmin, det_ymin, det_xmax, det_ymax, conf, cls = det
                if conf > 0.5 and int(cls) == 0:  # Only humans (class 0)
                    print(f"Human detected in Frame {frame_count:03d} - Confidence: {conf:.2f}")
                    if conf > highest_confidence:
                        highest_confidence = conf
                        best_frame = roi_frame.copy()  # Save the cropped ROI frame
                        best_bbox = (det_xmin, det_ymin, det_xmax, det_ymax)

            frame_count += 1

    except Exception as e:
        print(f"Error during detection: {e}")

    finally:
        cap.release()

    # Save the frame with the highest confidence (if any detection occurred)
    if best_frame is not None:
        try:
            frame_save_path = os.path.join(iteration_dir, "highest_confidence_frame.jpg")
            cv2.imwrite(frame_save_path, best_frame)
            print("Save path:", frame_save_path)

            # Assuming complement.generate_response exists
            try:
                complement_response = complement.generate_response(image_path=frame_save_path)
                print("------------------------------complement-----------------------------------\n", complement_response)
            except Exception as e:
                complement_response = "Error generating complement response."
                print(f"Complement generation error: {e}")

            humans_log_file.write(
                f"Frame {frame_count:03d}: Confidence: {highest_confidence:.2f}, "
                f"BBox: [{best_bbox[0]:.1f}, {best_bbox[1]:.1f}, {best_bbox[2]:.1f}, {best_bbox[3]:.1f}]\n"
            )
            humans_log_file.write(f"Complement: {complement_response}\n")

            # Assuming detection.load_detection_model exists
            try:
                detection_model = detection.load_detection_model()
                processed_frame = process_frame(best_frame, detection_model)

                if(processed_frame == True):
                    chatbot_session() 

                detect = np.squeeze(processed_frame.render())
                cv2.imshow('YOLO', detect)
            except Exception as e:
                print(f"Error processing frame with detection model: {e}")

            print(f"Saved frame with the highest confidence: {highest_confidence:.2f}")
            print(f"BBox: {best_bbox}")
        except Exception as e:
            print(f"Error saving frame or generating response: {e}")
    else:
        print("No human detections with confidence > 0.5.")

    print(f"Finished detecting humans. Logs saved in: {iteration_dir}")
    humans_log_file.close()
    chatbot_session() 

# Schedule the task to run every 2 minutes
schedule.every(1).minutes.do(detect_humans)
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