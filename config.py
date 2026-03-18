"""
Application Configuration
Smart Student Attendance System
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # Use C: drive for database since D: is full
    _default_sqlite = f"sqlite:///C:/Temp/smartattendance.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', _default_sqlite)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    FACES_FOLDER = os.path.join(UPLOAD_FOLDER, 'faces')
    QRCODES_FOLDER = os.path.join(UPLOAD_FOLDER, 'qrcodes')

    # Email configuration (Brevo)
    # Prefer BREVO_* env vars; fallback to generic MAIL_* for backward compatibility
    MAIL_SERVER = os.environ.get('BREVO_SMTP_HOST') or os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT = int(os.environ.get('BREVO_SMTP_PORT') or os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = (os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true')
    MAIL_USERNAME = os.environ.get('BREVO_SMTP_USER') or os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('BREVO_SMTP_PASS') or os.environ.get('MAIL_PASSWORD', '')
    _sender_email = os.environ.get('BREVO_SENDER_EMAIL') or os.environ.get('MAIL_DEFAULT_SENDER', '')
    _sender_name = os.environ.get('BREVO_SENDER_NAME', '').strip()
    MAIL_DEFAULT_SENDER = f'"{_sender_name}" <{_sender_email}>' if _sender_name else (_sender_email or 'noreply@smartattendance.com')

    # Face recognition
    FACE_RECOGNITION_TOLERANCE = float(os.environ.get('FACE_TOLERANCE', 0.5))
    FACE_ENCODING_MODEL = 'large'  # 'small' for faster, 'large' for accuracy

    # Attendance
    ATTENDANCE_THRESHOLD = int(os.environ.get('ATTENDANCE_THRESHOLD', 75))  # percentage

    # Session
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
