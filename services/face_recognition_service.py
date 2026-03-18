"""
Face Recognition Service
Uses face_recognition library (dlib-based) for encoding and verification.
Optional: app runs without it if dlib/face_recognition are not installed.
"""
import os
import json
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from flask import current_app

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False

_NOT_AVAILABLE_MSG = (
    "Face recognition is not available. Install CMake and then: "
    "pip install dlib face_recognition"
)
# Expose for routes (e.g. allow registration without encoding when unavailable)
NOT_AVAILABLE_MSG = _NOT_AVAILABLE_MSG


class FaceRecognitionService:
    """Handles face detection, encoding, and verification."""

    @staticmethod
    def decode_base64_image(base64_string):
        """Decode a base64-encoded image string to a numpy array."""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]

            image_data = base64.b64decode(base64_string)
            image = Image.open(BytesIO(image_data)).convert('RGB')
            return np.array(image)
        except Exception as e:
            current_app.logger.error(f"Error decoding base64 image: {e}")
            return None

    @staticmethod
    def detect_face(image_array):
        """Detect faces in an image array. Returns face locations."""
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        face_locations = face_recognition.face_locations(image_array, model='hog')
        return face_locations

    @staticmethod
    def get_face_encoding(image_array):
        """
        Get 128-dimensional face encoding from an image.
        Returns the encoding as a list, or None if no face found.
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return None, _NOT_AVAILABLE_MSG
        try:
            face_locations = face_recognition.face_locations(image_array, model='hog')

            if not face_locations:
                return None, "No face detected in the image. Please ensure your face is clearly visible."

            if len(face_locations) > 1:
                return None, "Multiple faces detected. Please ensure only your face is in the frame."

            model = current_app.config.get('FACE_ENCODING_MODEL', 'large')
            encodings = face_recognition.face_encodings(
                image_array,
                known_face_locations=face_locations,
                model=model
            )

            if not encodings:
                return None, "Could not generate face encoding. Please try again."

            return encodings[0].tolist(), None
        except Exception as e:
            current_app.logger.error(f"Error getting face encoding: {e}")
            return None, f"Face processing error: {str(e)}"

    @staticmethod
    def save_face_image(image_array, filename):
        """Save a face image to the uploads/faces directory."""
        try:
            faces_folder = current_app.config['FACES_FOLDER']
            os.makedirs(faces_folder, exist_ok=True)
            filepath = os.path.join(faces_folder, filename)
            image = Image.fromarray(image_array)
            image.save(filepath, 'JPEG', quality=90)
            return filepath
        except Exception as e:
            current_app.logger.error(f"Error saving face image: {e}")
            return None

    @staticmethod
    def verify_face(live_encoding_list, stored_encoding_json):
        """
        Compare a live face encoding against a stored encoding.
        Returns (match: bool, distance: float, message: str)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return False, 1.0, _NOT_AVAILABLE_MSG
        try:
            tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.5)

            live_encoding = np.array(live_encoding_list)
            stored_encoding = np.array(json.loads(stored_encoding_json))

            # Calculate face distance
            distance = face_recognition.face_distance([stored_encoding], live_encoding)[0]
            match = distance <= tolerance

            if match:
                confidence = round((1 - distance) * 100, 1)
                return True, distance, f"Face verified successfully ({confidence}% confidence)"
            else:
                return False, distance, "Face verification failed. The face does not match."

        except Exception as e:
            current_app.logger.error(f"Error verifying face: {e}")
            return False, 1.0, f"Face verification error: {str(e)}"

    @staticmethod
    def encoding_to_json(encoding_list):
        """Serialize face encoding to JSON string for storage."""
        return json.dumps(encoding_list)

    @staticmethod
    def json_to_encoding(json_string):
        """Deserialize face encoding from JSON string."""
        return json.loads(json_string)
