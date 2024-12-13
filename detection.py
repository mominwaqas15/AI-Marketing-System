import torch
import cv2
import numpy as np
import torch
from matplotlib import pyplot as plt
import numpy as np
import cv2


def load_detection_model():
    return torch.hub.load('ultralytics/yolov5', 'custom', path=r'best.pt')

def process_frame(frame, detection_model):
    # Run the frame through the detection model
    results = detection_model(frame)
    detections = results.xyxy[0].cpu().numpy()  # Get detections

    for det in detections:
        xmin, ymin, xmax, ymax, conf, cls = det
        gesture = detection_model.names[int(cls)]  # Get gesture label
        print(gesture)
        # If "hi" gesture detected with confidence > 0.5, call the function
        if gesture == "hi" and conf > 0.5:
            return True

    # Render results on the frame
    return False

# Specify the image path directly
# cap = cv2.VideoCapture(0)
# while cap.isOpened():
#     ret, frame = cap.read()
#     detection_model = load_detection_model()
#     # print(detection_model.names)
#     frame = process_frame(frame, detection_model)
#     String = str(frame)
#     detect = np.squeeze(frame.render())
#     cv2.imshow('YOLO', detect)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break
# cap.release()
# cv2.destroyAllWindows()

# model = load_detection_model()
# frame_result = process_frame(frame="/home/abdx10/Documents/Tensorwave/yolov5/hi_gesture.jpg",detection_model=model)
# print(frame_result)

