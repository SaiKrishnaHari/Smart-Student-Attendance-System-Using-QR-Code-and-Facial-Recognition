"""
Smart Student Attendance System
Main Application Entry Point

A production-ready attendance system with:
- QR code-based identification
- Facial recognition-based identity verification
- Dual verification for proxy-proof attendance

Author: SmartAttendance Team
"""
import os
import sys
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from config import config
from models.models import db, User


def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure required directories exist
    os.makedirs(app.config.get('FACES_FOLDER', 'uploads/faces'), exist_ok=True)
    os.makedirs(app.config.get('QRCODES_FOLDER', 'uploads/qrcodes'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.attendance import attendance_bp
    from routes.face import face_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(face_bp)

    # Jinja filter: show datetimes in app timezone (IST)
    from utils.timezone_utils import utc_to_app_str
    @app.template_filter('ist_datetime')
    def ist_datetime_filter(dt, fmt='%b %d, %H:%M'):
        if dt is None:
            return ''
        return utc_to_app_str(dt, fmt=fmt)

    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return redirect(url_for('auth.login'))

    @app.errorhandler(500)
    def server_error(e):
        return '<h1>500 - Internal Server Error</h1><p>Something went wrong. Please try again.</p>', 500

    # Create database tables and run schema migrations for new columns
    with app.app_context():
        db.create_all()
        _migrate_attendance_columns(db)
        _create_default_admin(app)

        # Validate DeepFace (ArcFace) is available
        from services.deepface_service import validate_deepface_and_model
        ok, msg = validate_deepface_and_model()
        if not ok:
            print()
            print("=" * 70)
            print("  FACE RECOGNITION (DeepFace) CHECK FAILED")
            print("=" * 70)
            print()
            print("  " + msg)
            print()
            print("  Install: pip install deepface")
            print("  Then run the app again.")
            print()
            print("=" * 70)
            sys.exit(1)
        print("[Startup] " + msg)

    return app


def _migrate_attendance_columns(db_instance):
    """Add new columns to attendance tables if missing (e.g. scheduled_start_at, grace_period_minutes, minutes_late)."""
    from sqlalchemy import text
    conn = db_instance.engine.connect()
    try:
        # SQLite: add columns if not present (ignore error if already exist)
        for stmt in [
            "ALTER TABLE attendance_sessions ADD COLUMN scheduled_start_at DATETIME",
            "ALTER TABLE attendance_sessions ADD COLUMN grace_period_minutes INTEGER NOT NULL DEFAULT 10",
            "ALTER TABLE attendance_records ADD COLUMN minutes_late INTEGER",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        conn.close()


def _create_default_admin(app):
    """Create a default admin account if none exists."""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            full_name='Admin',
            email='admin@smartattendance.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        app.logger.info('Default admin created: admin@smartattendance.com / admin123')


# Create the application
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Smart Student Attendance System")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    print("\n  Default Admin Login:")
    print("    Email:    admin@smartattendance.com")
    print("    Password: admin123")
    print("\n" + "=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
