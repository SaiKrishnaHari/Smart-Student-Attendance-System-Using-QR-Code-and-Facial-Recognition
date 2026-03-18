#!/usr/bin/env python3
"""
Send a single test email via Brevo (SMTP).
Usage: python send_test_email.py [recipient@example.com]
If no address is given, uses BREVO_SENDER_EMAIL from .env.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def main():
    to_email = (sys.argv[1] if len(sys.argv) > 1 else '').strip() or os.environ.get('BREVO_SENDER_EMAIL', '')
    if not to_email or '@' not in to_email:
        print('Usage: python send_test_email.py recipient@example.com')
        print('Or set BREVO_SENDER_EMAIL in .env and run: python send_test_email.py')
        sys.exit(1)

    host = os.environ.get('BREVO_SMTP_HOST', 'smtp-relay.brevo.com')
    port = int(os.environ.get('BREVO_SMTP_PORT', 587))
    user = os.environ.get('BREVO_SMTP_USER', '')
    password = os.environ.get('BREVO_SMTP_PASS', '')
    sender_email = os.environ.get('BREVO_SENDER_EMAIL', '')
    sender_name = os.environ.get('BREVO_SENDER_NAME', 'SmartAttendance').strip()
    from_addr = f'"{sender_name}" <{sender_email}>' if sender_name else sender_email

    if not user or not password:
        print('Error: Set BREVO_SMTP_USER and BREVO_SMTP_PASS in .env')
        sys.exit(1)

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart('related')
    msg['Subject'] = 'Smart Attendance – Brevo test email'
    msg['From'] = from_addr
    msg['To'] = to_email
    html = f"""
    <html><body style="font-family: sans-serif; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #f8fafc; border-radius: 12px; padding: 24px;">
            <h2 style="color: #1a1a2e;">Brevo test</h2>
            <p>This is a test email from the <strong>Smart Student Attendance System</strong>.</p>
            <p>If you received this, Brevo SMTP is configured correctly.</p>
            <p style="color: #94a3b8; font-size: 12px;">Sent to: {to_email}</p>
        </div>
    </body></html>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        print(f'Test email sent to {to_email}')
    except Exception as e:
        print(f'Failed to send: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
