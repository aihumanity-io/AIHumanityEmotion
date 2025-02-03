"""
Facial Emotion Detection Script

This script detects facial landmarks and extracts different facial regions
from an input image using MediaPipe. It then processes these extracted regions
and feeds them into a trained TensorFlow model for emotion classification.

Modules Used:
- os: To handle file operations and environment variables.
- sys: For system-level operations.
- numpy: For numerical computations.
- matplotlib.pyplot: For visualization.
- cv2 (OpenCV): For image processing.
- PIL (Pillow): For image handling.
- tensorflow: For machine learning model inference.
- pandas: For handling tabular data.
- mediapipe: For face landmark detection.
- re: For regular expressions.
- datetime: For timestamping output files.

Author: David Chiu, AIHumanity
Date: Feb 2, 2025
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import cv2
from PIL import Image
import tensorflow as tf
import pandas as pd
import mediapipe as mp
import re
import datetime

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'

# Define input image size
INPUT_SIZE = (224, 224, 3)

# Mapping emotion indices to emotion labels
idx_to_class = {
    0: 'Anger', 1: 'Disgust', 2: 'Fear', 3: 'Happiness',
    4: 'Neutral', 5: 'Sadness', 6: 'Surprise'
}

# Initialize MediaPipe face mesh module
mp_face_mesh = mp.solutions.face_mesh

def dateString():
    """Returns the current date and time as a formatted string."""
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def extract_landmark_images(image, pad=0):
    """
    Detects facial landmarks using MediaPipe and extracts different facial features.
    Returns a dictionary of cropped images for different facial parts.
    """
    face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.5)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)
    if not results.multi_face_landmarks:
        return None

    h, w, _ = image.shape
    landmarks = results.multi_face_landmarks[0].landmark

    def get_bbox(indices):
        points = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices])
        return cv2.boundingRect(points.astype(int))

    def pad_bbox(indices, pad):
        """Adds padding to bounding box coordinates."""
        x, y, w, h = get_bbox(indices)
        return max(x - pad, 0), min(x + w + pad, w), max(y - pad, 0), min(y + h + pad, h)
    
    # Define indices for different facial features
    left_eye_indices = [33, 133, 157, 158, 159, 160, 161, 173, 246]
    right_eye_indices = [362, 263, 386, 387, 388, 389, 390, 398, 466]
    mouth_indices = [0, 11, 12, 13, 14, 15, 16, 17, 37, 40, 61, 78, 81, 84, 87, 88, 91]
    face_indices = list(range(0, 468))
    
    # Extract feature images
    (x0, x1, y0, y1) = pad_bbox(left_eye_indices, pad)
    left_eye = image[y0:y1, x0:x1]
    (x0, x1, y0, y1) = pad_bbox(right_eye_indices, pad)
    right_eye = image[y0:y1, x0:x1]
    (x0, x1, y0, y1) = pad_bbox(mouth_indices, pad)
    mouth = image[y0:y1, x0:x1]
    (x0, x1, y0, y1) = pad_bbox(face_indices, 0)
    face = image[y0:y1, x0:x1]
    
    face_mesh.close()
    return {'left_eye': left_eye, 'right_eye': right_eye, 'mouth': mouth, 'face': face}

def load_image(file):
    """Loads an image, extracts facial regions, and preprocesses them for model input."""
    image = cv2.imread(file)
    landmark_images = extract_landmark_images(image)
    if not landmark_images:
        print("No face detected in the image.")
        return None
    
    images = [landmark_images['left_eye'], landmark_images['right_eye'], landmark_images['face'], landmark_images['mouth']]
    output = []
    for img in images:
        img = cv2.resize(img, (224, 224)).astype(np.float32)
        img[..., 0] -= 103.939
        img[..., 1] -= 116.779
        img[..., 2] -= 123.68
        output.append(tf.convert_to_tensor(img, dtype=tf.float32))
    
    return output if len(output) == 4 else None

def test_model(loaded_model, image_file):
    """Tests the model with a given image file and prints the predicted emotion."""
    if not os.path.exists(image_file):
        print(f"File not found: {image_file}")
        return
    
    images = load_image(image_file)
    if not images:
        print(f"Image {image_file} cannot be processed. No face detected.")
        return
    
    left, right, face, mouth = images
    inputs = [np.expand_dims(img, axis=0) for img in (left, right, face, mouth)]
    predictions = loaded_model.predict(inputs)[0]
    index_max = np.argmax(predictions)
    result = f"{image_file}, {predictions[index_max]}, {idx_to_class[index_max]}, {index_max}\n"
    print(result)
    return result

def main():
    """Main function to load the model, test images, and print results."""
    saved_model_file = 'aih_emotion_model.keras'
    test_image_file = 'test_image.png'
    print(f"Testing model: {saved_model_file} with image: {test_image_file}")
    
    loaded_model = tf.keras.models.load_model(saved_model_file)
    print(f"Devices available: {tf.config.list_physical_devices()}")
    
    strategy = tf.distribute.MirroredStrategy()
    print(f"Number of devices: {strategy.num_replicas_in_sync}")
    
    test_model(loaded_model, test_image_file)
    print("Testing complete.")

if __name__ == "__main__":
    main()
