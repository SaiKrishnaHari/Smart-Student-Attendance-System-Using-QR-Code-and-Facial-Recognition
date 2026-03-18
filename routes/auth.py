"""
Authentication Routes
Handles login, logout, and registration routing.
"""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.models import db, User
from services.deepface_service import DeepFaceService
from services.qr_service import QRService
from services.email_service import EmailService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact admin.', 'error')
                return render_template('auth/login.html')

            login_user(user)
            next_page = request.args.get('next')

            if user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            return redirect(next_page or url_for('student.dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle student registration."""
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        return _handle_registration()

    return render_template('auth/register.html')


@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for registration with face capture."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        student_id = data.get('student_id', '').strip()
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        branch = data.get('branch', '').strip()
        face_image_base64 = data.get('face_image', '')

        # Validation
        errors = []
        if not student_id:
            errors.append('Student ID is required.')
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if not branch:
            errors.append('Branch is required.')
        if not face_image_base64:
            errors.append('Face image is required.')

        if errors:
            return jsonify({'success': False, 'message': ' '.join(errors)}), 400

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 400
        if User.query.filter_by(student_id=student_id).first():
            return jsonify({'success': False, 'message': 'This Student ID is already registered.'}), 400

        # Process face image (DeepFace ArcFace)
        image_array = DeepFaceService.decode_base64_image(face_image_base64)
        if image_array is None:
            return jsonify({'success': False, 'message': 'Invalid face image. Please try again.'}), 400

        embedding, error = DeepFaceService.get_embedding(image_array)
        if error:
            return jsonify({'success': False, 'message': error}), 400

        # Save face image
        face_filename = f"face_{student_id}.jpg"
        face_path = DeepFaceService.save_face_image(image_array, face_filename)
        face_encoding_json = DeepFaceService.encoding_to_json(embedding)

        # Create user
        user = User(
            student_id=student_id,
            full_name=full_name,
            email=email,
            branch=branch,
            role='student',
            face_encoding=face_encoding_json,
            face_image_path=face_path
        )
        user.set_password(password)

        # Save to database first to generate public_id
        db.session.add(user)
        db.session.flush()  # This generates the public_id without committing

        # Generate QR code with the now-available public_id
        qr_service = QRService()
        qr_token = qr_service.generate_qr_token(student_id, user.public_id)
        user.qr_token = qr_token

        qr_path, qr_filename = qr_service.generate_qr_image(qr_token, full_name)
        if qr_path:
            user.qr_code_path = qr_path

        # Commit all changes
        db.session.commit()

        # Send QR code via email (non-blocking, don't fail registration if email fails)
        email_msg = ""
        if qr_path:
            email_service = EmailService()
            email_success, email_msg = email_service.send_qr_email(email, full_name, qr_path)

        return jsonify({
            'success': True,
            'message': f'Registration successful! {email_msg}',
            'redirect': url_for('auth.login')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500


def _handle_registration():
    """Handle form-based registration (fallback)."""
    flash('Please use the registration form with camera capture.', 'info')
    return redirect(url_for('auth.register'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
