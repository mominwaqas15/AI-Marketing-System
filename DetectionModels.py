import cv2
import torch
import os
import time
from datetime import datetime
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HumanDetection:
    def __init__(self, rtsp_url, output_dir, roi_coords, model_name='yolov5n', confidence_threshold=0.3, detection_duration=0.5):
        """
        Initializes the HumanDetection class.

        :param rtsp_url: RTSP stream URL for video input.
        :param output_dir: Directory to save detection logs and frames.
        :param roi_coords: Tuple (xmin, ymin, xmax, ymax) specifying the Region of Interest (ROI). 
        :param model_name: Name of the YOLOv5 model to load (default: yolov5n).
        :param confidence_threshold: Minimum confidence for detections (default: 0.5).
        :param detection_duration: Duration (in seconds) to run detection (default: 3 seconds).
        """
        self.rtsp_url = rtsp_url
        self.output_dir = output_dir
        self.xmin, self.ymin, self.xmax, self.ymax = roi_coords
        self.confidence_threshold = confidence_threshold
        self.detection_duration = detection_duration

        # Initialize YOLO model for person detection
        self.person_detection_model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)

        # Initialize MediaPipe Gesture Recognizer
        base_options = python.BaseOptions(model_asset_path='gesture_recognizer.task')
        gesture_options = vision.GestureRecognizerOptions(base_options=base_options)
        self.gesture_recognizer = vision.GestureRecognizer.create_from_options(gesture_options)

    def process_frame_for_gesture(self, frame_path):
        """
        Processes a single frame for gesture detection using MediaPipe.

        :param frame_path: Path to the saved frame.
        :return: List of detected gestures with confidence scores.
        """
        try:
            image = mp.Image.create_from_file(frame_path)
            recognition_result = self.gesture_recognizer.recognize(image)

            if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                return [
                    {
                        "gesture": gesture.category_name,
                        "confidence": float(gesture.score)
                    }
                    for gesture in recognition_result.gestures[0]
                ]
            else:
                return []

        except Exception as e:
            print(f"Error during gesture recognition: {e}")
            return []

    def detect_humans(self):
        """
        Performs human detection on the given RTSP stream within the specified ROI.
        Saves logs and the frame with the highest confidence.
        """ 

        # FOR stream
        # cap = cv2.VideoCapture(self.rtsp_url)

        # For Machine Camera
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Could not open RTSP stream.")
            return False, None, None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        iteration_dir = os.path.join(self.output_dir, timestamp)
        os.makedirs(iteration_dir, exist_ok=True)

        humans_log_path = os.path.join(iteration_dir, "human_detections.txt")
        humans_log_file = open(humans_log_path, "w")

        frame_count = 0
        start_time = time.time()

        highest_confidence = 0  # Track highest-confidence detection
        best_frame = None  
        best_bbox = None  # Bounding box of the highest-confidence detection

        try:
            while time.time() - start_time < self.detection_duration:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("Error: Failed to grab frame.")
                    time.sleep(1)
                    continue

                # Crop the frame to the ROI
                # roi_frame = frame[self.ymin:self.ymax, self.xmin:self.xmax]
                roi_frame = frame

                # Detect objects in the cropped ROI frame using YOLO
                results = self.person_detection_model(roi_frame)
                detections = results.xyxy[0].cpu().numpy()  # Bounding boxes, confidence, class

                for det in detections:
                    det_xmin, det_ymin, det_xmax, det_ymax, conf, cls = det
                    if conf > self.confidence_threshold and int(cls) == 0:  # Class 0 is human
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
                print(f"Saved frame with the highest confidence: {highest_confidence:.2f}")
                print(f"BBox: {best_bbox}")

                humans_log_file.write(
                    f"Frame {frame_count:03d}: Confidence: {highest_confidence:.2f}, "
                    f"BBox: [{best_bbox[0]:.1f}, {best_bbox[1]:.1f}, {best_bbox[2]:.1f}, {best_bbox[3]:.1f}]\n"
                )
                humans_log_file.close()
                return True, best_frame, frame_save_path
            except Exception as e:
                print(f"Error saving frame or writing to log: {e}")
        else:
            print("No human detected with sufficient confidence.")
            humans_log_file.close()
            return False, None, None

# Example Usage
if __name__ == "__main__":
    rtsp_url = "rtsp://admin:Ashton2012@41.222.89.66:560"
    output_dir = "Human-Detection-Logs"
    roi_coords = (400, 650, 2600, 2500)

    detector = HumanDetection(rtsp_url, output_dir, roi_coords)
    detection_success, best_frame, frame_path = detector.detect_humans()

    if detection_success:
        print("Detection completed successfully.")
        gestures = detector.process_frame_for_gesture(frame_path)
        print("Detected Gestures:", gestures)
    else:
        print("Detection failed or no humans detected.")