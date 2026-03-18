"""
Face Registration and Verification using DeepFace (ArcFace).
Windows-friendly: no dlib dependency. Uses OpenCV-compatible stack.
"""
import os
import json
import base64
import tempfile
import numpy as np
from io import BytesIO
from PIL import Image
from flask import current_app

# Lazy import to allow startup check
_DeepFace = None
_DEEPFACE_AVAILABLE = None


def _ensure_deepface():
    """Import DeepFace once and cache availability."""
    global _DeepFace, _DEEPFACE_AVAILABLE
    if _DEEPFACE_AVAILABLE is not None:
        return _DEEPFACE_AVAILABLE
    try:
        from deepface import DeepFace
        _DeepFace = DeepFace
        _DEEPFACE_AVAILABLE = True
        return True
    except ImportError as e:
        _DEEPFACE_AVAILABLE = False
        current_app.logger.warning(f"DeepFace not available: {e}") if current_app else None
        return False


def is_deepface_available():
    """Return True if DeepFace can be imported."""
    return _ensure_deepface()


def validate_deepface_and_model():
    """
    Startup check: ensure DeepFace loads and ArcFace model can be used.
    Returns (success: bool, message: str).
    """
    try:
        from deepface import DeepFace
    except ImportError as e:
        return False, f"DeepFace is not installed: {e}. Run: pip install deepface"
    model_name = current_app.config.get("DEEPFACE_MODEL", "ArcFace")
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            Image.new("RGB", (112, 112), color=(128, 128, 128)).save(f.name)
            path = f.name
        try:
            DeepFace.represent(path, model_name=model_name, enforce_detection=False)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        return True, f"DeepFace and {model_name} are ready."
    except Exception as e:
        return False, f"DeepFace model check failed: {e}"


class DeepFaceService:
    """Face registration and verification using DeepFace ArcFace embeddings."""

    MODEL_NAME = "ArcFace"

    @staticmethod
    def decode_base64_image(base64_string):
        """Decode base64 image string to numpy RGB array. Returns None on error."""
        try:
            if "," in base64_string:
                base64_string = base64_string.split(",", 1)[1]
            image_data = base64.b64decode(base64_string)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            return np.array(image)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error decoding base64 image: {e}")
            return None

    @staticmethod
    def get_embedding(image_input):
        """
        Detect exactly one face and return its ArcFace embedding.
        image_input: file path (str), numpy array (H,W,3), or base64 string.
        Returns (embedding_list, error_message). error_message is None on success.
        """
        if not _ensure_deepface():
            return None, "Face recognition (DeepFace) is not available."

        model_name = current_app.config.get("DEEPFACE_MODEL", DeepFaceService.MODEL_NAME)
        try:
            if isinstance(image_input, str) and ("base64" in image_input or ("," in image_input and len(image_input) > 100)):
                image_input = DeepFaceService.decode_base64_image(image_input)
                if image_input is None:
                    return None, "Invalid image data."
            if isinstance(image_input, np.ndarray):
                # Write to temp file; DeepFace.represent accepts path or np in some versions
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    Image.fromarray(image_input).save(f.name, "JPEG", quality=95)
                    path = f.name
                try:
                    representations = _DeepFace.represent(
                        path,
                        model_name=model_name,
                        enforce_detection=True,
                        detector_backend="opencv",
                    )
                finally:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            else:
                path = image_input
                representations = _DeepFace.represent(
                    path,
                    model_name=model_name,
                    enforce_detection=True,
                    detector_backend="opencv",
                )

            if not representations:
                return None, "No face detected. Please ensure your face is clearly visible and well lit."
            if len(representations) > 1:
                return None, "Multiple faces detected. Please ensure only your face is in the frame."

            embedding = representations[0].get("embedding")
            if embedding is None:
                return None, "Could not extract face embedding. Please try again in better lighting."
            return list(embedding), None

        except Exception as e:
            err = str(e).lower()
            if "face" in err and "detect" in err:
                return None, "No face detected. Please ensure your face is clearly visible and well lit."
            if "multiple" in err or "more than one" in err:
                return None, "Multiple faces detected. Please ensure only your face is in the frame."
            if current_app:
                current_app.logger.exception("DeepFace get_embedding error")
            return None, "Face processing failed. Please try again in good lighting and ensure only one face is visible."

    @staticmethod
    def verify(live_embedding_list, stored_embedding_json):
        """
        Compare live embedding to stored embedding (JSON string or list).
        Returns (verified: bool, similarity_score: float, message: str).
        Uses cosine similarity; threshold from config.
        """
        if not _ensure_deepface():
            return False, 0.0, "Face recognition (DeepFace) is not available."

        try:
            stored = stored_embedding_json
            if isinstance(stored, str):
                stored = json.loads(stored)
            a = np.array(live_embedding_list, dtype=np.float64)
            b = np.array(stored, dtype=np.float64)
            a_norm = a / (np.linalg.norm(a) + 1e-10)
            b_norm = b / (np.linalg.norm(b) + 1e-10)
            similarity = float(np.dot(a_norm, b_norm))
            threshold = current_app.config.get("FACE_SIMILARITY_THRESHOLD", 0.5)
            verified = similarity >= threshold

            if verified:
                msg = f"Face verified (similarity: {similarity:.2f})"
            else:
                msg = "Face does not match. Please use your own face to mark attendance."
            return verified, similarity, msg
        except Exception as e:
            if current_app:
                current_app.logger.exception("DeepFace verify error")
            return False, 0.0, f"Verification error: {str(e)}"

    @staticmethod
    def save_face_image(image_array, filename):
        """Save face image to uploads/faces. Returns file path or None."""
        try:
            folder = current_app.config["FACES_FOLDER"]
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            Image.fromarray(image_array).save(path, "JPEG", quality=90)
            return path
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error saving face image: {e}")
            return None

    @staticmethod
    def encoding_to_json(embedding_list):
        return json.dumps(embedding_list)

    @staticmethod
    def json_to_encoding(json_string):
        return json.loads(json_string)
