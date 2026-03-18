# Smart Student Attendance System

A production-ready, proxy-proof attendance system using **QR code** and **facial recognition** for dual verification. Built with Flask, SQLite, and pre-trained face recognition (no ML training required).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Smart Attendance System                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Frontend (HTML/CSS/JS)                                                  │
│  • Poppins font, light/dark theme, responsive layout                     │
│  • Webcam capture (registration + attendance)                            │
│  • QR scanner (jsQR), Chart.js for analytics                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Backend (Flask)                                                         │
│  • Auth: login, register, logout (Flask-Login, hashed passwords)        │
│  • Student: dashboard, attendance page, stats API                         │
│  • Admin: dashboard, sessions CRUD, students list, reports API           │
│  • Attendance API: /api/attendance/verify (QR + face dual check)         │
├─────────────────────────────────────────────────────────────────────────┤
│  Services                                                                │
│  • FaceRecognitionService: encode face, verify against stored embedding   │
│  • QRService: generate signed QR token, validate, generate image        │
│  • EmailService: send QR code to student (optional)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  Data (SQLite → PostgreSQL-ready)                                         │
│  • users (students + admin), attendance_sessions, attendance_records    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

- **Student registration**: Student ID, name, email, password, branch + live face capture → unique QR + optional email.
- **Dual verification**: Attendance is marked only when both QR identity and face match the registered user (proxy-proof).
- **Admin/Teacher**: Start/stop sessions, view live count, students list with search/filter, daily/weekly/monthly reports, defaulter list, charts.
- **UI**: Light/dark theme toggle, Poppins font, cards, toasts, loading states, step-by-step flows.

---

## Project Structure

```
smartattendance/
├── app.py                 # Entry point, app factory
├── config.py              # Config + env
├── requirements.txt
├── .env.example
├── models/
│   ├── __init__.py
│   └── models.py          # User, AttendanceSession, AttendanceRecord
├── routes/
│   ├── __init__.py
│   ├── auth.py            # login, register, logout, api/register
│   ├── student.py         # dashboard, attendance page, APIs
│   ├── admin.py           # dashboard, sessions, students, reports
│   └── attendance.py      # api/attendance/verify
├── services/
│   ├── __init__.py
│   ├── face_recognition_service.py
│   ├── qr_service.py
│   └── email_service.py
├── static/
│   ├── css/style.css      # Theme variables, layout, components
│   └── js/
│       ├── theme.js       # Light/dark toggle
│       ├── app.js         # Toasts, loading, sidebar
│       ├── camera.js      # Webcam start/stop, capture frame
│       └── charts.js      # Trend + branch charts
├── templates/
│   ├── base.html          # Layout, sidebar, theme toggle
│   ├── auth/login.html, auth/register.html
│   ├── student/dashboard.html, student/attendance.html
│   └── admin/dashboard.html, admin/sessions.html, admin/students.html, admin/reports.html
├── uploads/
│   ├── faces/             # Stored face images
│   └── qrcodes/           # Generated QR images
└── instance/              # SQLite DB (gitignored)
```

---

## Database Schema

| Table | Key Fields |
|-------|------------|
| **users** | id, public_id, student_id, full_name, email, password_hash, branch, role, face_encoding, face_image_path, qr_code_path, qr_token |
| **attendance_sessions** | id, session_code, title, description, branch, created_by, is_active, started_at, ended_at |
| **attendance_records** | id, student_id, session_id, qr_verified, face_verified, status, marked_at | Unique (student_id, session_id) |

---

## API Flow (Attendance Marking)

1. **Student** opens attendance page for an active session.
2. **Frontend** starts QR scanner (camera + jsQR) → on detect, stores `qr_data`, moves to “Face verify” step.
3. **Frontend** starts face camera → user clicks “Verify & Mark Attendance” → captures frame as base64.
4. **POST /api/attendance/verify** with `{ session_id, qr_data, face_image }`.
5. **Backend**: validate session active, no duplicate record; decode QR → validate HMAC → ensure QR matches logged-in user; decode face → get encoding → compare with stored encoding; if both pass → insert `AttendanceRecord` (qr_verified, face_verified, status=present).
6. **Response**: success + record details or error message.

---

## Setup

### 1. Prerequisites

- Python 3.10+
- **Face recognition (required):** The app uses the `face_recognition` library (depends on `dlib`). On **Windows**, `pip install dlib` often fails; see **[FACE_RECOGNITION_SETUP.md](FACE_RECOGNITION_SETUP.md)** for step-by-step instructions (pre-built wheel or CMake + Visual Studio Build Tools). On Linux/macOS, install system deps (e.g. `cmake`, `build-essential`) then `pip install dlib face_recognition`.

### 2. Install

```bash
cd smartattendance
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 3. Environment

```bash
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux
```

Edit `.env`: set `SECRET_KEY`, and set Brevo variables (`BREVO_SMTP_*`, `BREVO_SENDER_*`) to send QR codes by email via [Brevo](https://www.brevo.com/).

### 4. Run

```bash
python app.py
```

- Open **http://127.0.0.1:5000**
- **Default admin**: `admin@smartattendance.com` / `admin123`
- Register a student (with face capture), then log in as student and mark attendance when a session is active.

---

## Error Handling Strategy

- **Auth**: Invalid login → flash message; unauthenticated access → redirect to login.
- **Registration**: Validation + face encoding errors → JSON error and toast; duplicate email/student_id → 400 with message.
- **Attendance**: Session not found/ended → 404/400; duplicate attendance → 400; QR invalid/tampered → 400; QR not matching user → 403; face mismatch → 403; server errors → 500, rollback DB.
- **UI**: Toasts for success/error; loading overlay during verify; step-by-step flow with clear messages.

---

## Client Demo Checklist

- [ ] Admin can log in and create an attendance session (title, optional branch).
- [ ] Student can register (ID, name, email, password, branch) and capture face; QR is generated (and emailed if configured).
- [ ] Student can log in and see dashboard with active sessions and QR code.
- [ ] Student can open “Mark Attendance” for an active session, scan QR then verify face; attendance is marked and success screen shown.
- [ ] Same student cannot mark attendance twice for the same session.
- [ ] Another person scanning the same QR but different face is rejected (proxy blocked).
- [ ] Admin can stop session, view session records, view students (search/filter), and open reports (overview, trend, branch, defaulters).
- [ ] Light/dark theme toggle works; layout is responsive.

---

## Deployment Notes

- Set `FLASK_ENV=production` and a strong `SECRET_KEY`.
- For production DB: set `DATABASE_URL` to a PostgreSQL connection string (SQLAlchemy supports it with the same models).
- Use **gunicorn** (Linux/macOS) or **waitress** (Windows): `gunicorn -w 4 -b 0.0.0.0:5000 "app:app"`.
- Serve static files via a reverse proxy (e.g. Nginx) in production for better performance.
- Keep `uploads/` and `instance/` outside version control; back up database and uploads.

---

## License & Credits

Built for educational institutions. Uses [face_recognition](https://github.com/ageitgey/face_recognition), [Flask](https://flask.palletsprojects.com/), [Chart.js](https://www.chartjs.org/), [Lucide icons](https://lucide.dev/), [jsQR](https://github.com/cozmo/jsQR).
