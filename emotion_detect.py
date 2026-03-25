# emotion_detect.py
import cv2
import numpy as np
import time
from deepface import DeepFace

# -------------------------------
# CONFIGURATION
# -------------------------------
CONF_THRESHOLD = 0.55      # 55% confidence
STABLE_TIME = 2.0          # seconds emotion must remain stable

# Emotion mapping from DeepFace to our 4 categories
EMOTION_MAP = {
    'happy': 'happy',
    'sad': 'sad',
    'neutral': 'neutral',
    'angry': 'angry',
    'fear': 'angry',
    'surprise': 'happy',
    'disgust': 'angry'
}

# -------------------------------
# LOAD FACE DETECTOR (once)
# -------------------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# -------------------------------
# STATE VARIABLES (for stability)
# -------------------------------
prev_box = None
stable_emotion = None
emotion_start_time = None
recommendation_done = False

print("✅ Emotion detection ready using DeepFace")

# -------------------------------
# MAIN FUNCTION FOR STREAMLIT
# -------------------------------
def detect_emotion_from_frame(frame):
    """
    Input:
        frame (numpy array, BGR format from OpenCV)

    Returns:
        emotion (str or None)
        confidence (float 0-1)
        stable_triggered (bool)
        face_box (tuple or None)
    """

    global prev_box, stable_emotion, emotion_start_time, recommendation_done

    try:
        # Resize frame for faster processing
        frame = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=7,
            minSize=(100, 100)
        )

        if len(faces) == 0:
            # Reset stability if no face detected
            stable_emotion = None
            emotion_start_time = None
            recommendation_done = False
            return None, 0.0, False, None

        # Pick largest face
        faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
        (x, y, w, h) = faces[0]

        # Smooth bounding box for stability
        if prev_box is None:
            prev_box = (x, y, w, h)
        else:
            px, py, pw, ph = prev_box
            prev_box = (
                int(px * 0.7 + x * 0.3),
                int(py * 0.7 + y * 0.3),
                int(pw * 0.7 + w * 0.3),
                int(ph * 0.7 + h * 0.3)
            )

        (x, y, w, h) = prev_box
        face_region = frame[y:y+h, x:x+w]

        if face_region.size == 0:
            return None, 0.0, False, None

        # Convert BGR to RGB for DeepFace
        face_rgb = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)

        # Analyze emotion using DeepFace
        result = DeepFace.analyze(
            face_rgb, 
            actions=['emotion'], 
            enforce_detection=False, 
            silent=True
        )

        if result and len(result) > 0:
            raw_emotion = result[0]['dominant_emotion']
            confidence = result[0]['emotion'][raw_emotion] / 100.0

            # Map to our 4 emotions
            emotion = EMOTION_MAP.get(raw_emotion, 'neutral')
            
            # -------------------------------
            # STABLE EMOTION LOGIC
            # -------------------------------
            current_time = time.time()
            stable_triggered = False

            if confidence >= CONF_THRESHOLD:
                if emotion != stable_emotion:
                    stable_emotion = emotion
                    emotion_start_time = current_time
                    recommendation_done = False
                else:
                    elapsed = current_time - emotion_start_time
                    if elapsed >= STABLE_TIME and not recommendation_done:
                        recommendation_done = True
                        stable_triggered = True

            return emotion, confidence, stable_triggered, (x, y, w, h)

        return None, 0.0, False, None

    except Exception as e:
        print(f"Error in emotion detection: {e}")
        return None, 0.0, False, None