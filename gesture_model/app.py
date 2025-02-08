import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
import csv
import copy
import itertools
from collections import Counter, deque
import argparse

import cv2 as cv
import numpy as np
import mediapipe as mp

from gesture_model.utils import CvFpsCalc
from gesture_model.model import KeyPointClassifier, PointHistoryClassifier

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use_static_image_mode', action='store_true')
    parser.add_argument("--min_detection_confidence", type=float, default=0.7)
    parser.add_argument("--min_tracking_confidence", type=float, default=0.5)
    return parser.parse_args()

def gesture_detection(image):
    # Argument parsing
    args = get_args()
    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    # Model initialization
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=1,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    keypoint_classifier = KeyPointClassifier()
    point_history_classifier = PointHistoryClassifier()

    # Load labels
    with open('gesture_model/model/keypoint_classifier/keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]
    with open('gesture_model/model/point_history_classifier/point_history_classifier_label.csv', encoding='utf-8-sig') as f:
        point_history_classifier_labels = [row[0] for row in csv.reader(f)]

    # Process the image
    image = cv.flip(image, 1)  # Mirror display
    debug_image = copy.deepcopy(image)
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

    # Process with Mediapipe
    results = hands.process(image)

    gesture_result = "No Hand Detected"
    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Landmark calculation
            landmark_list = calc_landmark_list(debug_image, hand_landmarks)

            # Preprocess landmarks
            pre_processed_landmark_list = pre_process_landmark(landmark_list)

            # Hand sign classification
            hand_sign_id = keypoint_classifier(pre_processed_landmark_list)

            # Finger gesture classification
            finger_gesture_id = 0
            if hand_sign_id == 2:  # Example: Point gesture
                finger_gesture_id = point_history_classifier(pre_processed_landmark_list)

            # Get gesture labels
            gesture_result = keypoint_classifier_labels[hand_sign_id]
            debug_image = draw_landmarks(debug_image, landmark_list)
            debug_image = draw_info_text(debug_image, [0, 0, 200, 30], handedness, keypoint_classifier_labels[hand_sign_id], point_history_classifier_labels[finger_gesture_id])

    return gesture_result

def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point.append([landmark_x, landmark_y])
    return landmark_point

def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)
    base_x, base_y = temp_landmark_list[0]
    for index in range(len(temp_landmark_list)):
        temp_landmark_list[index][0] -= base_x
        temp_landmark_list[index][1] -= base_y
    max_value = max(list(map(abs, itertools.chain.from_iterable(temp_landmark_list))))
    temp_landmark_list = [n / max_value for n in itertools.chain.from_iterable(temp_landmark_list)]
    return temp_landmark_list

def draw_landmarks(image, landmark_point):
    for i, landmark in enumerate(landmark_point):
        color = (0, 255, 0) if i % 4 == 0 else (255, 0, 0)
        cv.circle(image, tuple(landmark), 5, color, 2)
    return image

def draw_info_text(image, brect, handedness, hand_sign_text, finger_gesture_text):
    cv.putText(image, f"{handedness.classification[0].label}: {hand_sign_text}", (brect[0] + 5, brect[1] - 4),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)
    if finger_gesture_text != "":
        cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)
    return image

# Example usage:
image = cv.imread('/content/AI-Marketing-System/hello_gesture.jpeg')
gesture = gesture_detection(image)
print(f"Detected Gesture: {gesture}")
# cv.imshow("Gesture", debug_img)
cv.waitKey(0)
cv.destroyAllWindows()
