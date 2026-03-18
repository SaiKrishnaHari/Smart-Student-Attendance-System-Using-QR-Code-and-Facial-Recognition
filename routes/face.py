"""
Face registration and verification API (DeepFace ArcFace).
POST /api/face/register  - validate image, return embedding for storage.
POST /api/face/verify    - compare image to stored embedding; return verified + score.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from services.deepface_service import DeepFaceService, is_deepface_available
from models.models import User

face_bp = Blueprint("face", __name__, url_prefix="/api/face")


@face_bp.route("/register", methods=["POST"])
def register_face():
    """
    Accept a captured image (base64 or file), detect exactly one face,
    return ArcFace embedding for the caller to store.
    Body: { "image": "<base64>" } or multipart file "image".
    """
    if not is_deepface_available():
        return jsonify({
            "success": False,
            "message": "Face recognition (DeepFace) is not available.",
        }), 503

    image_input = None
    if request.is_json:
        data = request.get_json() or {}
        image_input = data.get("image") or data.get("face_image")
    if not image_input and request.files:
        file = request.files.get("image") or request.files.get("file")
        if file:
            import base64
            image_input = "data:image/jpeg;base64," + base64.b64encode(file.read()).decode("utf-8")

    if not image_input:
        return jsonify({
            "success": False,
            "message": "No image provided. Send 'image' as base64 or file upload.",
        }), 400

    embedding, error = DeepFaceService.get_embedding(image_input)
    if error:
        return jsonify({
            "success": False,
            "message": error,
        }), 400

    return jsonify({
        "success": True,
        "embedding": embedding,
        "message": "Face detected and embedding generated.",
    })


@face_bp.route("/verify", methods=["POST"])
@login_required
def verify_face():
    """
    Compare a live-captured image to the stored face embedding.
    Body: { "image": "<base64>" } (uses current user's stored embedding).
    Optional: { "image": "<base64>", "stored_embedding": [...] } to compare against given embedding.
    """
    if not is_deepface_available():
        return jsonify({
            "success": False,
            "verified": False,
            "message": "Face recognition (DeepFace) is not available.",
        }), 503

    image_input = None
    stored_embedding = None
    if request.is_json:
        data = request.get_json() or {}
        image_input = data.get("image") or data.get("face_image")
        stored_embedding = data.get("stored_embedding")
    if not image_input and request.files:
        file = request.files.get("image") or request.files.get("file")
        if file:
            import base64
            image_input = "data:image/jpeg;base64," + base64.b64encode(file.read()).decode("utf-8")

    if not image_input:
        return jsonify({
            "success": False,
            "verified": False,
            "message": "No image provided. Send 'image' as base64 or file upload.",
        }), 400

    if stored_embedding is None:
        if not current_user.is_authenticated:
            return jsonify({
                "success": False,
                "verified": False,
                "message": "Authentication required or provide 'stored_embedding'.",
            }), 401
        if not getattr(current_user, "face_encoding", None):
            return jsonify({
                "success": False,
                "verified": False,
                "message": "No face data on file for this user.",
            }), 400
        stored_embedding = current_user.face_encoding

    live_embedding, error = DeepFaceService.get_embedding(image_input)
    if error:
        return jsonify({
            "success": False,
            "verified": False,
            "message": error,
        }), 400

    verified, similarity, msg = DeepFaceService.verify(live_embedding, stored_embedding)
    current_app.logger.info(
        f"Face verify user_id={getattr(current_user, 'id', None)} verified={verified} similarity={similarity:.4f}"
    )

    return jsonify({
        "success": True,
        "verified": verified,
        "similarity_score": round(similarity, 4),
        "message": msg,
    })
