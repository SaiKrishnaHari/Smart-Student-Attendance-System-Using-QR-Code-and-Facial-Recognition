"""
Student Routes
Handles student dashboard and profile.
"""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import db, User, AttendanceSession, AttendanceRecord
from services.qr_service import QRService
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import now_app, app_day_start_end_utc

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    """Decorator to ensure user is a student."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('Access denied. Students only.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard with attendance overview."""
    # Get attendance stats
    total_sessions = AttendanceSession.query.filter(
        AttendanceSession.ended_at.isnot(None)
    ).count()

    attended = AttendanceRecord.query.filter(
        AttendanceRecord.student_id == current_user.id,
        AttendanceRecord.status.in_(['present', 'late'])
    ).count()

    attendance_pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 0

    # Recent attendance records
    recent_records = db.session.query(
        AttendanceRecord, AttendanceSession
    ).join(
        AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
    ).filter(
        AttendanceRecord.student_id == current_user.id
    ).order_by(
        AttendanceRecord.marked_at.desc()
    ).limit(10).all()

    # Active sessions
    active_sessions = AttendanceSession.query.filter_by(is_active=True).all()

    # Get QR code base64 for display
    qr_base64 = None
    if current_user.qr_code_path:
        qr_service = QRService()
        qr_base64 = qr_service.get_qr_base64(current_user.qr_code_path)

    return render_template('student/dashboard.html',
                           total_sessions=total_sessions,
                           attended=attended,
                           attendance_pct=attendance_pct,
                           recent_records=recent_records,
                           active_sessions=active_sessions,
                           qr_base64=qr_base64)


@student_bp.route('/attendance/<int:session_id>')
@login_required
@student_required
def attendance_page(session_id):
    """Attendance marking page for a specific session."""
    session = AttendanceSession.query.get_or_404(session_id)

    if not session.is_active:
        flash('This attendance session has ended.', 'error')
        return redirect(url_for('student.dashboard'))

    # Check if already marked
    existing = AttendanceRecord.query.filter_by(
        student_id=current_user.id,
        session_id=session_id
    ).first()

    if existing:
        flash('You have already marked attendance for this session.', 'info')
        return redirect(url_for('student.dashboard'))

    return render_template('student/attendance.html', session=session)


@student_bp.route('/api/attendance-history')
@login_required
@student_required
def attendance_history():
    """API: Get student's attendance history."""
    records = db.session.query(
        AttendanceRecord, AttendanceSession
    ).join(
        AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
    ).filter(
        AttendanceRecord.student_id == current_user.id
    ).order_by(
        AttendanceRecord.marked_at.desc()
    ).all()

    history = []
    for record, session in records:
        history.append({
            'session_title': session.title,
            'session_code': session.session_code,
            'date': record.marked_at.strftime('%Y-%m-%d'),
            'time': record.marked_at.strftime('%H:%M:%S'),
            'status': record.status,
            'qr_verified': record.qr_verified,
            'face_verified': record.face_verified
        })

    return jsonify({'success': True, 'history': history})


@student_bp.route('/api/stats')
@login_required
@student_required
def student_stats():
    """API: Get student attendance statistics."""
    total_sessions = AttendanceSession.query.filter(
        AttendanceSession.ended_at.isnot(None)
    ).count()

    attended = AttendanceRecord.query.filter(
        AttendanceRecord.student_id == current_user.id,
        AttendanceRecord.status.in_(['present', 'late'])
    ).count()

    attendance_pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 0

    # Weekly data (last 7 days, IST)
    now_ist = now_app()
    weekly_data = []
    for i in range(6, -1, -1):
        day_ist = now_ist - timedelta(days=i)
        day_start, day_end = app_day_start_end_utc(day_ist)

        day_attended = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == current_user.id,
            AttendanceRecord.status.in_(['present', 'late']),
            AttendanceRecord.marked_at >= day_start,
            AttendanceRecord.marked_at <= day_end
        ).count()

        weekly_data.append({
            'day': day_ist.strftime('%a'),
            'date': day_ist.strftime('%Y-%m-%d'),
            'attended': day_attended
        })

    return jsonify({
        'success': True,
        'total_sessions': total_sessions,
        'attended': attended,
        'attendance_pct': attendance_pct,
        'weekly_data': weekly_data
    })
