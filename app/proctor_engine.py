import cv2
import numpy as np
import base64
import time
from pathlib import Path
from datetime import datetime
from app.config import SNAPSHOTS_DIR, MODELS_DIR

FACE_CASCADE_PATH = MODELS_DIR / "haarcascade_frontalface_default.xml"
EYE_CASCADE_PATH = MODELS_DIR / "haarcascade_eye.xml"

# Initialize cascades safely
face_cascade = None
eye_cascade = None
try:
    if hasattr(cv2, "CascadeClassifier") and FACE_CASCADE_PATH.exists():
        face_cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
    if hasattr(cv2, "CascadeClassifier") and EYE_CASCADE_PATH.exists():
        eye_cascade = cv2.CascadeClassifier(str(EYE_CASCADE_PATH))
except Exception as e:
    print("Warning: Cascade classifier init:", e)

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decodes a base64 data URI into an OpenCV BGR image"""
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    image_bytes = base64.b64decode(base64_string)
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return image

def analyze_frame(image: np.ndarray):
    """
    Analyzes an exam frame for:
    - Number of faces detected
    - Lighting condition / average brightness
    - Eye count / head pose clues
    """
    if image is None:
        return {
            "face_count": 0,
            "status": "INVALID_IMAGE",
            "brightness": 0,
            "message": "Unable to decode image"
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    # Detect faces
    faces = []
    if face_cascade is not None:
        try:
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60)
            )
        except Exception:
            faces = []

    face_count = len(faces)
    face_boxes = []
    eye_count = 0

    for (x, y, w, h) in faces:
        face_boxes.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
        eye_count += len(eyes)

    status = "NORMAL"
    reason = "Face verified"

    if brightness < 35:
        status = "LOW_LIGHT"
        reason = "Room lighting is too dim. Please ensure adequate lighting."
    elif face_count == 0:
        status = "NO_FACE"
        reason = "No face detected in webcam view."
    elif face_count > 1:
        status = "MULTIPLE_FACES"
        reason = f"Multiple faces detected ({face_count} persons)!"
    elif eye_count == 0:
        # Looking down or eyes occluded
        status = "SUSPICIOUS_POSE"
        reason = "Candidate may be looking away or eyes are not visible."

    return {
        "face_count": face_count,
        "face_boxes": face_boxes,
        "eye_count": eye_count,
        "brightness": round(brightness, 1),
        "status": status,
        "reason": reason
    }

def save_violation_snapshot(image: np.ndarray, session_id: str, violation_type: str) -> str:
    """
    Annotates the frame with red bounding box, violation watermark, and saves to disk.
    Returns the saved filename.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{session_id}_{violation_type}_{timestamp_str}.jpg"
    filepath = SNAPSHOTS_DIR / filename

    annotated = image.copy()
    h, w = annotated.shape[:2]

    # Draw banner on top
    cv2.rectangle(annotated, (0, 0), (w, 50), (20, 20, 180), -1)
    text = f"VIOLATION: {violation_type} | {datetime.now().strftime('%H:%M:%S')}"
    cv2.putText(
        annotated,
        text,
        (15, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    # Save to disk
    cv2.imwrite(str(filepath), annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return filename
