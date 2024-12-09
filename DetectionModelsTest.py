import os
import cv2
import time
from datetime import datetime
import torch


class HumanDetection:
    def __init__(self, output_dir, model_name='yolov5n', confidence_threshold=0.5, detection_duration=3):
        """
        Initializes the HumanDetection class.
        
        :param output_dir: Directory to save detection logs and frames.
        :param model_name: Name of the YOLOv5 model to load (default: yolov5n).
        :param confidence_threshold: Minimum confidence for detections (default: 0.5).
        :param detection_duration: Duration (in seconds) to run detection (default: 3 seconds).
        """
        self.output_dir = output_dir
        self.confidence_threshold = confidence_threshold
        self.detection_duration = detection_duration
        self.person_detection_model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
        self.gesture_detection_model = self.load_gesture_detection_model()

    def load_gesture_detection_model(self):
        """
        Loads the custom YOLOv5 model for gesture detection.
        """
        try:
            model = torch.hub.load('ultralytics/yolov5', 'custom', path=r'best.pt')
            print("Gesture detection model loaded successfully.")
            return model
        except Exception as e:
            print(f"Error loading gesture detection model: {e}")
            return None

    def process_frame_for_gesture(self, frame):
        """
        Processes a single frame for gesture detection using the custom model. 
        Detects if a "hi" gesture is present.
        
        :param frame: The frame to process.
        :return: True if "hi" gesture is detected with confidence > 0.5, False otherwise.
        """
        if not self.gesture_detection_model:
            print("Gesture detection model is not loaded.")
            return False

        results = self.gesture_detection_model(frame)
        detections = results.xyxy[0].cpu().numpy()  # Get detections

        for det in detections:
            xmin, ymin, xmax, ymax, conf, cls = det
            gesture = self.gesture_detection_model.names[int(cls)]  # Get gesture label
            print(f"Gesture detected: {gesture}, Confidence: {conf:.2f}")
            if gesture == "hi" and conf > 0.5:
                return True  

        return False

    def detect_humans(self):
        """
        Performs human detection on the laptop's camera feed.
        Saves logs and the frame with the highest confidence.
        """
        cap = cv2.VideoCapture(0)  # Open the laptop camera
        if not cap.isOpened():
            print("Error: Could not access laptop camera.")
            return False, None, None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        iteration_dir = os.path.join(self.output_dir, timestamp)
        os.makedirs(iteration_dir, exist_ok=True)

        humans_log_path = os.path.join(iteration_dir, "human_detections.txt")
        humans_log_file = open(humans_log_path, "w")

        frame_count = 0
        start_time = time.time()

        highest_confidence = 0  # Track highest-confidence detection
        best_frame = None  # Frame with highest-confidence detection
        best_bbox = None  # Bounding box of the highest-confidence detection

        try:
            while time.time() - start_time < self.detection_duration:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("Error: Failed to grab frame.")
                    time.sleep(1)
                    continue

                # Detect objects in the full frame
                results = self.person_detection_model(frame)
                detections = results.xyxy[0].cpu().numpy()  # Bounding boxes, confidence, class

                for det in detections:
                    det_xmin, det_ymin, det_xmax, det_ymax, conf, cls = det
                    if conf > self.confidence_threshold and int(cls) == 0:  # Class 0 is human
                        print(f"Human detected in Frame {frame_count:03d} - Confidence: {conf:.2f}")
                        if conf > highest_confidence:
                            highest_confidence = conf
                            best_frame = frame.copy()  # Save the full frame
                            best_bbox = (det_xmin, det_ymin, det_xmax, det_ymax)

                # Process the frame for gesture detection
                if self.process_frame_for_gesture(frame):
                    print("Hi gesture detected!")
                    # You can perform any additional action here, e.g., sending an alert.

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
    output_dir = "Human-Detection-Logs"

    detector = HumanDetection(output_dir)
    detection_success, best_frame, save_path = detector.detect_humans()

    if detection_success:
        print(f"Detection completed successfully. Frame saved at {save_path}.")
    else:
        print("Detection failed or no humans detected.")
