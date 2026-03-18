"""
Admin/Teacher Routes
Handles admin dashboard, session management, and reports.
"""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_required, current_user
from models.models import db, User, AttendanceSession, AttendanceRecord, AppSetting
from sqlalchemy import func, desc
from datetime import datetime, timedelta, timezone
from services.email_service import EmailService
from utils.timezone_utils import (
    now_utc,
    app_today_start_end_utc,
    app_day_start_end_utc,
    parse_datetime_as_app_then_utc,
    utc_to_app_str,
    utc_to_app_date_str,
    utc_to_app_time_str,
    get_app_tz,
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to ensure user is an admin/teacher."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin/Teacher only.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def _get_default_grace_period_minutes():
    """Default grace period: admin setting if set, else config/env."""
    row = AppSetting.query.filter_by(key='default_grace_period_minutes').first()
    if row and row.value is not None:
        try:
            return int(row.value)
        except (ValueError, TypeError):
            pass
    return current_app.config.get('DEFAULT_GRACE_PERIOD_MINUTES', 10)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with overview stats (today = IST day)."""
    today_start, today_end = app_today_start_end_utc()
    total_students = User.query.filter_by(role='student', is_active=True).count()
    total_sessions = AttendanceSession.query.count()
    active_sessions = AttendanceSession.query.filter_by(is_active=True).count()
    today_records = AttendanceRecord.query.filter(
        AttendanceRecord.marked_at >= today_start,
        AttendanceRecord.marked_at <= today_end
    ).count()

    # Today's breakdown: present, late, absent (today = IST)
    present_today = AttendanceRecord.query.filter(
        AttendanceRecord.status == 'present',
        AttendanceRecord.marked_at >= today_start,
        AttendanceRecord.marked_at <= today_end
    ).count()
    late_today = AttendanceRecord.query.filter(
        AttendanceRecord.status == 'late',
        AttendanceRecord.marked_at >= today_start,
        AttendanceRecord.marked_at <= today_end
    ).count()
    attended_today = present_today + late_today
    distinct_attended = db.session.query(func.count(func.distinct(AttendanceRecord.student_id))).filter(
        AttendanceRecord.marked_at >= today_start,
        AttendanceRecord.marked_at <= today_end
    ).scalar() or 0
    absent_today = max(0, total_students - distinct_attended)
    attendance_pct_today = round((distinct_attended / total_students * 100), 1) if total_students > 0 else 0

    # Recent sessions
    recent_sessions = AttendanceSession.query.order_by(
        AttendanceSession.started_at.desc()
    ).limit(5).all()

    # Get branches
    branches = db.session.query(User.branch).filter(
        User.role == 'student',
        User.branch.isnot(None)
    ).distinct().all()
    branches = [b[0] for b in branches if b[0]]

    return render_template('admin/dashboard.html',
                           total_students=total_students,
                           total_sessions=total_sessions,
                           active_sessions=active_sessions,
                           today_records=today_records,
                           present_today=present_today,
                           late_today=late_today,
                           absent_today=absent_today,
                           attendance_pct_today=attendance_pct_today,
                           recent_sessions=recent_sessions,
                           branches=branches)


@admin_bp.route('/api/settings')
@login_required
@admin_required
def get_settings():
    """Get admin-editable settings (e.g. default grace period)."""
    default_grace = _get_default_grace_period_minutes()
    return jsonify({
        'success': True,
        'settings': {
            'default_grace_period_minutes': default_grace
        }
    })


@admin_bp.route('/api/settings', methods=['PATCH', 'PUT'])
@login_required
@admin_required
def update_settings():
    """Update admin-editable settings."""
    try:
        data = request.get_json() or {}
        if 'default_grace_period_minutes' in data:
            val = data['default_grace_period_minutes']
            try:
                n = int(val)
                if n < 0 or n > 120:
                    return jsonify({'success': False, 'message': 'Grace period must be between 0 and 120 minutes.'}), 400
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Invalid grace period value.'}), 400
            row = AppSetting.query.filter_by(key='default_grace_period_minutes').first()
            if row:
                row.value = str(n)
            else:
                db.session.add(AppSetting(key='default_grace_period_minutes', value=str(n)))
            db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Settings saved.',
            'settings': {'default_grace_period_minutes': _get_default_grace_period_minutes()}
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Settings update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/test-email', methods=['POST'])
@login_required
@admin_required
def send_test_email():
    """Send a test email via Brevo to verify SMTP configuration."""
    try:
        data = request.get_json() or {}
        to_email = (data.get('to') or request.form.get('to') or '').strip() or current_user.email

        if not to_email or '@' not in to_email:
            return jsonify({'success': False, 'message': 'Please provide a valid email address.'}), 400

        success, msg = EmailService.send_test_email(to_email)

        if success:
            return jsonify({'success': True, 'message': f'Test email sent to {to_email}.'})
        return jsonify({'success': False, 'message': msg}), 500
    except Exception as e:
        current_app.logger.error(f"Test email error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/sessions')
@login_required
@admin_required
def sessions():
    """Manage attendance sessions."""
    all_sessions = AttendanceSession.query.order_by(
        AttendanceSession.started_at.desc()
    ).all()

    branches = db.session.query(User.branch).filter(
        User.role == 'student',
        User.branch.isnot(None)
    ).distinct().all()
    branches = [b[0] for b in branches if b[0]]

    return render_template('admin/sessions.html',
                           sessions=all_sessions,
                           branches=branches)


@admin_bp.route('/api/sessions', methods=['POST'])
@login_required
@admin_required
def create_session():
    """Create a new attendance session."""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        branch = data.get('branch', '').strip()

        if not title:
            return jsonify({'success': False, 'message': 'Session title is required.'}), 400

        scheduled_start_at = None
        if data.get('scheduled_start_at'):
            scheduled_start_at = parse_datetime_as_app_then_utc(data['scheduled_start_at'])
        grace_period_minutes = data.get('grace_period_minutes')
        if grace_period_minutes is not None:
            try:
                grace_period_minutes = int(grace_period_minutes)
            except (TypeError, ValueError):
                grace_period_minutes = _get_default_grace_period_minutes()
        else:
            grace_period_minutes = _get_default_grace_period_minutes()

        session = AttendanceSession(
            title=title,
            description=description,
            branch=branch if branch else None,
            created_by=current_user.id,
            is_active=True,
            scheduled_start_at=scheduled_start_at,
            grace_period_minutes=grace_period_minutes
        )

        db.session.add(session)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Session "{title}" started!',
            'session': {
                'id': session.id,
                'session_code': session.session_code,
                'title': session.title,
                'branch': session.branch,
                'started_at': session.started_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create session error: {e}")
        return jsonify({'success': False, 'message': 'Failed to create session.'}), 500


@admin_bp.route('/api/sessions/<int:session_id>/stop', methods=['POST'])
@login_required
@admin_required
def stop_session(session_id):
    """Stop an active attendance session."""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        session.is_active = False
        session.ended_at = now_utc()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Session "{session.title}" has been stopped.',
            'attendance_count': session.attendance_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to stop session.'}), 500


@admin_bp.route('/api/sessions/<int:session_id>/records')
@login_required
@admin_required
def session_records(session_id):
    """Get attendance records for a specific session."""
    session = AttendanceSession.query.get_or_404(session_id)

    records = db.session.query(
        AttendanceRecord, User
    ).join(
        User, AttendanceRecord.student_id == User.id
    ).filter(
        AttendanceRecord.session_id == session_id
    ).order_by(
        AttendanceRecord.marked_at.desc()
    ).all()

    record_list = []
    for record, student in records:
        record_list.append({
            'student_id': student.student_id,
            'student_name': student.full_name,
            'branch': student.branch,
            'time': utc_to_app_time_str(record.marked_at),
            'qr_verified': record.qr_verified,
            'face_verified': record.face_verified,
            'status': record.status or 'present',
            'minutes_late': getattr(record, 'minutes_late', None)
        })

    return jsonify({
        'success': True,
        'session': {
            'title': session.title,
            'session_code': session.session_code,
            'attendance_count': session.attendance_count
        },
        'records': record_list
    })


@admin_bp.route('/students')
@login_required
@admin_required
def students():
    """View registered students."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    branch_filter = request.args.get('branch', '', type=str)

    query = User.query.filter_by(role='student')

    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.student_id.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )

    if branch_filter:
        query = query.filter_by(branch=branch_filter)

    students_list = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    branches = db.session.query(User.branch).filter(
        User.role == 'student',
        User.branch.isnot(None)
    ).distinct().all()
    branches = [b[0] for b in branches if b[0]]

    return render_template('admin/students.html',
                           students=students_list,
                           search=search,
                           branch_filter=branch_filter,
                           branches=branches)


@admin_bp.route('/students/<int:student_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_student(student_id):
    """Delete a student and all their attendance records."""
    import os
    student = User.query.filter_by(id=student_id, role='student').first()
    
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'}), 404
    
    try:
        # Delete attendance records first
        AttendanceRecord.query.filter_by(student_id=student.id).delete()
        
        # Delete face image if exists
        if student.face_image_path and os.path.exists(student.face_image_path):
            os.remove(student.face_image_path)
        
        # Delete QR code if exists
        if student.qr_code_path and os.path.exists(student.qr_code_path):
            os.remove(student.qr_code_path)
        
        # Delete the student
        db.session.delete(student)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Student {student.full_name} deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Attendance reports and analytics."""
    branches = db.session.query(User.branch).filter(
        User.role == 'student',
        User.branch.isnot(None)
    ).distinct().all()
    branches = [b[0] for b in branches if b[0]]

    return render_template('admin/reports.html', branches=branches)


@admin_bp.route('/api/analytics/dashboard')
@login_required
@admin_required
def analytics_dashboard():
    """API: Analytics summary, bar data (7 days), pie data (today), student-wise %. Today = IST."""
    try:
        now = now_utc()
        branch = request.args.get('branch', '')
        today_start, today_end = app_today_start_end_utc()

        students_query = User.query.filter_by(role='student', is_active=True)
        if branch:
            students_query = students_query.filter_by(branch=branch)
        total_students = students_query.count()

        present_today = AttendanceRecord.query.filter(
            AttendanceRecord.status == 'present',
            AttendanceRecord.marked_at >= today_start,
            AttendanceRecord.marked_at <= today_end
        )
        if branch:
            present_today = present_today.join(User, AttendanceRecord.student_id == User.id).filter(User.branch == branch)
        present_today = present_today.count()

        late_today = AttendanceRecord.query.filter(
            AttendanceRecord.status == 'late',
            AttendanceRecord.marked_at >= today_start,
            AttendanceRecord.marked_at <= today_end
        )
        if branch:
            late_today = late_today.join(User, AttendanceRecord.student_id == User.id).filter(User.branch == branch)
        late_today = late_today.count()

        q = db.session.query(func.count(func.distinct(AttendanceRecord.student_id))).filter(
            AttendanceRecord.marked_at >= today_start,
            AttendanceRecord.marked_at <= today_end
        )
        if branch:
            q = q.join(User, AttendanceRecord.student_id == User.id).filter(User.branch == branch)
        distinct_attended = q.scalar() or 0
        absent_today = max(0, total_students - distinct_attended)
        attendance_pct = round(((present_today + late_today) / total_students * 100), 1) if total_students > 0 else 0

        # Bar: last 7 days (attendance per day) — use IST day boundaries
        bar_data = []
        from utils.timezone_utils import now_app
        now_ist = now_app()
        for i in range(6, -1, -1):
            day_ist = now_ist - timedelta(days=i)
            day_start, day_end = app_day_start_end_utc(day_ist)
            total = AttendanceRecord.query.filter(
                AttendanceRecord.status.in_(['present', 'late']),
                AttendanceRecord.marked_at >= day_start,
                AttendanceRecord.marked_at <= day_end
            )
            if branch:
                total = total.join(User, AttendanceRecord.student_id == User.id).filter(User.branch == branch)
            total = total.count()
            late_d = AttendanceRecord.query.filter(
                AttendanceRecord.status == 'late',
                AttendanceRecord.marked_at >= day_start,
                AttendanceRecord.marked_at <= day_end
            )
            if branch:
                late_d = late_d.join(User, AttendanceRecord.student_id == User.id).filter(User.branch == branch)
            late_d = late_d.count()
            bar_data.append({
                'date': day_ist.strftime('%b %d'),
                'total': total,
                'late': late_d,
                'present': total - late_d
            })

        pie_data = {'present': present_today, 'late': late_today, 'absent': absent_today}

        # Student-wise attendance %
        start_date = now - timedelta(days=30)
        sessions_in_period = AttendanceSession.query.filter(
            AttendanceSession.started_at >= start_date
        )
        if branch:
            sessions_in_period = sessions_in_period.filter_by(branch=branch)
        total_sessions = sessions_in_period.count()
        students = students_query.all()
        student_wise = []
        for s in students:
            attended = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == s.id,
                AttendanceRecord.status.in_(['present', 'late']),
                AttendanceRecord.marked_at >= start_date
            ).count()
            pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 0
            student_wise.append({
                'student_id': s.student_id,
                'name': s.full_name,
                'branch': s.branch,
                'percentage': pct,
                'attended': attended,
                'total': total_sessions
            })
        student_wise.sort(key=lambda x: x['percentage'], reverse=True)

        return jsonify({
            'success': True,
            'summary': {
                'total_students': total_students,
                'present_today': present_today,
                'late_today': late_today,
                'absent_today': absent_today,
                'attendance_pct': attendance_pct
            },
            'bar_data': bar_data,
            'pie_data': pie_data,
            'student_wise': student_wise
        })
    except Exception as e:
        current_app.logger.error(f"Analytics dashboard error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/reports/overview')
@login_required
@admin_required
def reports_overview():
    """API: Get attendance overview statistics. Days use IST boundaries."""
    try:
        branch = request.args.get('branch', '')
        period = request.args.get('period', 'weekly')  # weekly, monthly

        now = now_utc()
        from utils.timezone_utils import now_app
        now_ist = now_app()

        if period == 'monthly':
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)

        # Total sessions in period
        sessions_query = AttendanceSession.query.filter(
            AttendanceSession.started_at >= start_date
        )
        if branch:
            sessions_query = sessions_query.filter_by(branch=branch)
        total_sessions = sessions_query.count()

        # Student attendance data
        students_query = User.query.filter_by(role='student', is_active=True)
        if branch:
            students_query = students_query.filter_by(branch=branch)

        students = students_query.all()
        threshold = current_app.config.get('ATTENDANCE_THRESHOLD', 75)

        student_stats = []
        defaulters = []

        for student in students:
            attended = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.status.in_(['present', 'late']),
                AttendanceRecord.marked_at >= start_date
            ).count()

            pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 0

            student_data = {
                'student_id': student.student_id,
                'name': student.full_name,
                'branch': student.branch,
                'attended': attended,
                'total': total_sessions,
                'percentage': pct
            }
            student_stats.append(student_data)

            if pct < threshold:
                defaulters.append(student_data)

        # Daily attendance trend (IST calendar days)
        trend_data = []
        days = 30 if period == 'monthly' else 7
        for i in range(days - 1, -1, -1):
            day_ist = now_ist - timedelta(days=i)
            day_start, day_end = app_day_start_end_utc(day_ist)

            day_count = AttendanceRecord.query.filter(
                AttendanceRecord.status.in_(['present', 'late']),
                AttendanceRecord.marked_at >= day_start,
                AttendanceRecord.marked_at <= day_end
            ).count()
            day_late = AttendanceRecord.query.filter(
                AttendanceRecord.status == 'late',
                AttendanceRecord.marked_at >= day_start,
                AttendanceRecord.marked_at <= day_end
            ).count()

            day_sessions = AttendanceSession.query.filter(
                AttendanceSession.started_at >= day_start,
                AttendanceSession.started_at <= day_end
            ).count()

            trend_data.append({
                'date': day_ist.strftime('%b %d'),
                'attendance_count': day_count,
                'late_count': day_late,
                'sessions': day_sessions
            })

        # Branch-wise breakdown
        branch_stats = []
        all_branches = db.session.query(User.branch).filter(
            User.role == 'student',
            User.branch.isnot(None)
        ).distinct().all()

        for b in all_branches:
            b_name = b[0]
            if not b_name:
                continue
            b_students = User.query.filter_by(role='student', branch=b_name, is_active=True).count()
            b_attended = db.session.query(func.count(AttendanceRecord.id)).join(
                User, AttendanceRecord.student_id == User.id
            ).filter(
                User.branch == b_name,
                AttendanceRecord.status.in_(['present', 'late']),
                AttendanceRecord.marked_at >= start_date
            ).scalar()

            branch_stats.append({
                'branch': b_name,
                'total_students': b_students,
                'total_attendance': b_attended or 0
            })

        return jsonify({
            'success': True,
            'total_sessions': total_sessions,
            'total_students': len(students),
            'threshold': threshold,
            'student_stats': sorted(student_stats, key=lambda x: x['percentage'], reverse=True),
            'defaulters': sorted(defaulters, key=lambda x: x['percentage']),
            'trend_data': trend_data,
            'branch_stats': branch_stats
        })

    except Exception as e:
        current_app.logger.error(f"Reports error: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate report.'}), 500


@admin_bp.route('/api/students/list')
@login_required
@admin_required
def api_students_list():
    """API: Get students list with search/filter."""
    search = request.args.get('search', '')
    branch = request.args.get('branch', '')

    query = User.query.filter_by(role='student')

    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.student_id.ilike(f'%{search}%')
            )
        )
    if branch:
        query = query.filter_by(branch=branch)

    students = query.order_by(User.full_name).all()

    total_sessions = AttendanceSession.query.filter(
        AttendanceSession.ended_at.isnot(None)
    ).count()

    student_list = []
    for s in students:
        attended = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == s.id,
            AttendanceRecord.status.in_(['present', 'late'])
        ).count()
        pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 0

        student_list.append({
            'id': s.id,
            'student_id': s.student_id,
            'name': s.full_name,
            'email': s.email,
            'branch': s.branch,
            'attendance_pct': pct,
            'registered_at': s.created_at.strftime('%Y-%m-%d'),
            'is_active': s.is_active
        })

    return jsonify({'success': True, 'students': student_list})


@admin_bp.route('/api/attendance/export')
@login_required
@admin_required
def attendance_export_csv():
    """Export attendance records as CSV for date range and optional branch."""
    try:
        from io import StringIO
        from csv import writer as csv_writer

        date_from = request.args.get('from', '')
        date_to = request.args.get('to', '')
        branch = request.args.get('branch', '').strip()

        from utils.timezone_utils import now_app
        now_ist = now_app()
        if not date_from:
            date_from = (now_ist - timedelta(days=7)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = now_ist.strftime('%Y-%m-%d')

        try:
            # Interpret date range as IST calendar days
            start_ist = datetime.strptime(date_from, '%Y-%m-%d').replace(tzinfo=get_app_tz())
            end_ist = datetime.strptime(date_to, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=get_app_tz()
            )
            start_dt = start_ist.astimezone(timezone.utc)
            end_dt = end_ist.astimezone(timezone.utc)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        query = db.session.query(AttendanceRecord, User, AttendanceSession).join(
            User, AttendanceRecord.student_id == User.id
        ).join(
            AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
        ).filter(
            AttendanceRecord.marked_at >= start_dt,
            AttendanceRecord.marked_at <= end_dt
        )
        if branch:
            query = query.filter(User.branch == branch)

        rows = query.order_by(AttendanceRecord.marked_at.desc()).all()

        buf = StringIO()
        w = csv_writer(buf)
        w.writerow(['Date', 'Time', 'Student ID', 'Student Name', 'Branch', 'Session', 'Status', 'Minutes Late'])
        for record, user, session in rows:
            w.writerow([
                utc_to_app_date_str(record.marked_at),
                utc_to_app_time_str(record.marked_at),
                user.student_id or '',
                user.full_name,
                user.branch or '',
                session.title,
                record.status or 'present',
                getattr(record, 'minutes_late', '') or ''
            ])
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=attendance_{date_from}_to_{date_to}.csv'}
        )
    except Exception as e:
        current_app.logger.error(f"CSV export error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
