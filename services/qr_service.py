"""
QR Code Service
Generates and validates unique QR codes for students.
"""
import os
import uuid
import json
import hmac
import hashlib
import qrcode
from io import BytesIO
from flask import current_app


class QRService:
    """Handles QR code generation and validation."""

    @staticmethod
    def generate_qr_token(student_id, public_id):
        """
        Generate a unique, signed QR token for a student.
        Token contains student identifier + HMAC signature for tamper protection.
        """
        secret = current_app.config['SECRET_KEY']
        payload = f"{public_id}:{student_id}"
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:16]

        token = f"{payload}:{signature}"
        return token

    @staticmethod
    def validate_qr_token(token):
        """
        Validate a QR token's HMAC signature.
        Returns (valid: bool, public_id: str or None, student_id: str or None)
        """
        try:
            secret = current_app.config['SECRET_KEY']
            parts = token.split(':')
            if len(parts) != 3:
                return False, None, None

            public_id, student_id, signature = parts
            payload = f"{public_id}:{student_id}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()[:16]

            if hmac.compare_digest(signature, expected_signature):
                return True, public_id, student_id
            return False, None, None
        except Exception as e:
            current_app.logger.error(f"QR token validation error: {e}")
            return False, None, None

    @staticmethod
    def generate_qr_image(token, student_name):
        """
        Generate a QR code image for the given token.
        Returns the file path of the saved QR code.
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )

            # Encode JSON payload in QR
            qr_data = json.dumps({
                'token': token,
                'system': 'SmartAttendance'
            })

            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="#1a1a2e", back_color="white")

            # Save QR code
            qr_folder = current_app.config['QRCODES_FOLDER']
            os.makedirs(qr_folder, exist_ok=True)

            filename = f"qr_{token.split(':')[1]}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(qr_folder, filename)
            img.save(filepath)

            return filepath, filename
        except Exception as e:
            current_app.logger.error(f"QR generation error: {e}")
            return None, None

    @staticmethod
    def get_qr_base64(filepath):
        """Get QR code image as base64 string for embedding in emails/pages."""
        try:
            with open(filepath, 'rb') as f:
                import base64
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"Error reading QR code: {e}")
            return None

    @staticmethod
    def decode_qr_data(qr_data_string):
        """
        Decode QR data from scanned QR code.
        Returns (token: str or None, error: str or None)
        """
        try:
            data = json.loads(qr_data_string)
            if data.get('system') != 'SmartAttendance':
                return None, "Invalid QR code - not from SmartAttendance system."
            token = data.get('token')
            if not token:
                return None, "Invalid QR code - missing token."
            return token, None
        except json.JSONDecodeError:
            return None, "Invalid QR code format."
        except Exception as e:
            return None, f"QR decode error: {str(e)}"
