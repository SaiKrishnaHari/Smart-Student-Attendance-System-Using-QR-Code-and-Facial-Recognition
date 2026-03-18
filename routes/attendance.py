"""
Attendance Routes
Handles the dual-verification attendance marking process.
"""
import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models.models import db, User, AttendanceSession, AttendanceRecord
from services.deepface_service import DeepFaceService
from services.qr_service import QRService
from utils.timezone_utils import utc_to_app_date_str, utc_to_app_time_str

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')


@attendance_bp.route('/verify', methods=['POST'])
@login_required
def verify_attendance():
    """
    Dual verification endpoint.
    Requires: QR code data + live face image.
    Process:
      1. Decode and validate QR code
      2. Match QR identity to logged-in user
      3. Capture and verify face against stored encoding
      4. Mark attendance if both checks pass
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        session_id = data.get('session_id')
        qr_data = data.get('qr_data', '')
        face_image_base64 = data.get('face_image', '')

        # Validate inputs
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required.'}), 400
        if not qr_data:
            return jsonify({'success': False, 'message': 'QR code data is required.'}), 400
        if not face_image_base64:
            return jsonify({'success': False, 'message': 'Face image is required.'}), 400

        # Check session exists and is active
        session = AttendanceSession.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'message': 'Attendance session not found.'}), 404
        if not session.is_active:
            return jsonify({'success': False, 'message': 'This attendance session has ended.'}), 400

        # Check for duplicate attendance
        existing = AttendanceRecord.query.filter_by(
            student_id=current_user.id,
            session_id=session_id
        ).first()
        if existing:
            return jsonify({
                'success': False,
                'message': 'You have already marked attendance for this session.'
            }), 400

        # ============================================
        # STEP 1: QR Code Verification
        # ============================================
        qr_service = QRService()
        token, qr_error = qr_service.decode_qr_data(qr_data)

        if qr_error:
            return jsonify({'success': False, 'message': f'QR Verification Failed: {qr_error}'}), 400

        # Validate token signature
        valid, public_id, student_id = qr_service.validate_qr_token(token)

        if not valid:
            return jsonify({
                'success': False,
                'message': 'QR code is invalid or has been tampered with.'
            }), 400

        # Verify QR belongs to the logged-in user
        if current_user.public_id != public_id or current_user.student_id != student_id:
            current_app.logger.warning(
                f"QR mismatch: User {current_user.id} (public_id={getattr(current_user, 'public_id', None)}, "
                f"student_id={getattr(current_user, 'student_id', None)}) vs QR (public_id={public_id}, student_id={student_id})"
            )
            if str(public_id).lower() == 'none':
                return jsonify({
                    'success': False,
                    'message': 'Your QR code is outdated or invalid. Please use the QR code from your dashboard, or contact admin to regenerate your QR code.'
                }), 403
            return jsonify({
                'success': False,
                'message': 'This QR code does not belong to your account. Use your own QR code from the dashboard or email.'
            }), 403

        qr_verified = True

        # ============================================
        # STEP 2: Face Verification
        # ============================================
        if not current_user.face_encoding:
            return jsonify({
                'success': False,
                'message': 'No face data on file. Please re-register with face capture.'
            }), 400

        # Decode live face image
        image_array = DeepFaceService.decode_base64_image(face_image_base64)
        if image_array is None:
            return jsonify({
                'success': False,
                'message': 'Could not process face image. Please try again.'
            }), 400

        # Get live embedding (DeepFace ArcFace)
        live_embedding, face_error = DeepFaceService.get_embedding(image_array)
        if face_error:
            return jsonify({'success': False, 'message': f'Face: {face_error}'}), 400

        # Compare with stored embedding
        face_verified, similarity, face_msg = DeepFaceService.verify(
            live_embedding, current_user.face_encoding
        )

        if not face_verified:
            current_app.logger.warning(
                f"Face mismatch for user {current_user.id} (similarity: {similarity:.4f})"
            )
            return jsonify({
                'success': False,
                'message': 'Face verification failed. Your face does not match our records.',
                'detail': 'This may happen due to poor lighting or camera angle. Please try again.'
            }), 403

        # ============================================
        # STEP 3: Mark Attendance
        # ============================================
        record = AttendanceRecord(
            student_id=current_user.id,
            session_id=session_id,
            qr_verified=qr_verified,
            face_verified=face_verified,
            status='present',
            ip_address=request.remote_addr
        )
        db.session.add(record)
        db.session.flush()  # so record.marked_at is set

        # Automatic late entry classification
        session_start = session.scheduled_start_at or session.started_at
        grace_minutes = getattr(session, 'grace_period_minutes', None) or current_app.config.get('DEFAULT_GRACE_PERIOD_MINUTES', 10)
        cutoff = session_start + timedelta(minutes=grace_minutes)
        # Use timezone-aware comparison (store and compare in UTC)
        marked_at = record.marked_at
        if marked_at.tzinfo is None:
            marked_at = marked_at.replace(tzinfo=timezone.utc)
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        if marked_at <= cutoff:
            record.status = 'present'
            record.minutes_late = None
            display_status = 'Present'
        else:
            record.status = 'late'
            mins_late = int((marked_at - cutoff).total_seconds() / 60)
            record.minutes_late = mins_late
            display_status = f'Late ({mins_late} minutes late)'

        db.session.commit()

        current_app.logger.info(
            f"Attendance marked: User {current_user.id} -> Session {session_id} "
            f"(QR: {qr_verified}, Face: {face_verified}, status={record.status})"
        )

        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully!',
            'attendance_status': record.status,
            'attendance_display': display_status,
            'detail': face_msg,
            'record': {
                'student_name': current_user.full_name,
                'session': session.title,
                'time': utc_to_app_time_str(record.marked_at),
                'date': utc_to_app_date_str(record.marked_at),
                'status': record.status,
                'minutes_late': record.minutes_late,
                'qr_verified': qr_verified,
                'face_verified': face_verified
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Attendance verification error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during verification. Please try again.'
        }), 500


@attendance_bp.route('/active-sessions', methods=['GET'])
@login_required
def active_sessions():
    """Get list of currently active attendance sessions."""
    sessions = AttendanceSession.query.filter_by(is_active=True).all()

    session_list = []
    for s in sessions:
        # Check if current student already marked
        already_marked = False
        if current_user.is_student:
            already_marked = AttendanceRecord.query.filter_by(
                student_id=current_user.id,
                session_id=s.id
            ).first() is not None

        session_list.append({
            'id': s.id,
            'session_code': s.session_code,
            'title': s.title,
            'description': s.description,
            'branch': s.branch,
            'started_at': s.started_at.strftime('%Y-%m-%d %H:%M'),
            'attendance_count': s.attendance_count,
            'already_marked': already_marked
        })

    return jsonify({'success': True, 'sessions': session_list})
