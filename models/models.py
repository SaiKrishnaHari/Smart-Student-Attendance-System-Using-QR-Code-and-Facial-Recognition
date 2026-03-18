"""
Database Models
Smart Student Attendance System
"""
import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for students and admins/teachers."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(50), unique=True, nullable=True)  # Only for students
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    branch = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student' or 'admin'
    face_encoding = db.Column(db.Text, nullable=True)  # JSON-serialized face embedding
    face_image_path = db.Column(db.String(300), nullable=True)
    qr_code_path = db.Column(db.String(300), nullable=True)
    qr_token = db.Column(db.String(100), unique=True, nullable=True)  # Unique token in QR
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f'<User {self.full_name} ({self.role})>'


class AttendanceSession(db.Model):
    """Attendance session created by teacher/admin."""
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_code = db.Column(db.String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4())[:8].upper())
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    branch = db.Column(db.String(100), nullable=True)  # Target branch
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)
    # Late entry: class start time (if None, use started_at); grace period in minutes
    scheduled_start_at = db.Column(db.DateTime, nullable=True)
    grace_period_minutes = db.Column(db.Integer, nullable=False, default=10)

    # Relationships
    creator = db.relationship('User', backref='created_sessions', foreign_keys=[created_by])
    records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic')

    @property
    def attendance_count(self):
        return self.records.count()

    @property
    def is_expired(self):
        return not self.is_active or self.ended_at is not None

    def __repr__(self):
        return f'<AttendanceSession {self.session_code} - {self.title}>'


class AttendanceRecord(db.Model):
    """Individual attendance record."""
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    qr_verified = db.Column(db.Boolean, default=False)
    face_verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='present')  # 'present', 'late', 'failed'
    minutes_late = db.Column(db.Integer, nullable=True)  # Set when status is 'late'
    marked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(50), nullable=True)

    # Ensure one attendance per student per session
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', name='unique_student_session'),
    )

    def __repr__(self):
        return f'<AttendanceRecord Student:{self.student_id} Session:{self.session_id}>'


class AppSetting(db.Model):
    """Key-value store for admin-configurable settings."""
    __tablename__ = 'app_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<AppSetting {self.key}={self.value}>'
