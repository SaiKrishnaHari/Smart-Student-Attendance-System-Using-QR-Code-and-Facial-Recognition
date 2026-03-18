"""
Email Service
Sends QR codes and notifications to students via email.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from flask import current_app


class EmailService:
    """Handles email sending for the attendance system."""

    @staticmethod
    def send_qr_email(recipient_email, student_name, qr_image_path):
        """
        Send QR code to student via email.
        Returns (success: bool, message: str)
        """
        try:
            mail_server = current_app.config.get('MAIL_SERVER')
            mail_port = current_app.config.get('MAIL_PORT')
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')  # Can be "Name <email>"
            use_tls = current_app.config.get('MAIL_USE_TLS', True)

            if not mail_username or not mail_password:
                current_app.logger.warning("Email credentials not configured. QR code saved locally.")
                return False, "Email not configured. QR code has been saved to your account."

            # Create message
            msg = MIMEMultipart('related')
            msg['Subject'] = 'Your Smart Attendance QR Code'
            msg['From'] = mail_sender
            msg['To'] = recipient_email

            # HTML body
            html_body = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                         background-color: #f0f2f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; 
                            border-radius: 12px; padding: 40px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #1a1a2e; margin: 0;">Smart Attendance</h1>
                        <p style="color: #6c757d; margin-top: 5px;">Secure Attendance System</p>
                    </div>
                    
                    <h2 style="color: #333;">Hello {student_name},</h2>
                    
                    <p style="color: #555; line-height: 1.6;">
                        Welcome to the Smart Attendance System! Your unique QR code has been 
                        generated. Please find it attached below.
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0; padding: 20px; 
                                background: #f8f9fa; border-radius: 8px;">
                        <img src="cid:qrcode" alt="Your QR Code" 
                             style="max-width: 250px; border-radius: 8px;">
                        <p style="color: #888; font-size: 12px; margin-top: 10px;">
                            Your unique attendance QR code
                        </p>
                    </div>
                    
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; 
                                padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <strong style="color: #856404;">Important:</strong>
                        <p style="color: #856404; margin: 5px 0 0 0; font-size: 14px;">
                            Do NOT share this QR code with anyone. Each attendance requires 
                            both your QR code AND face verification. Sharing your QR code 
                            will not allow proxy attendance.
                        </p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        Smart Attendance System &copy; 2026<br>
                        This is an automated email. Please do not reply.
                    </p>
                </div>
            </body>
            </html>
            """

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Attach QR code image
            if os.path.exists(qr_image_path):
                with open(qr_image_path, 'rb') as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header('Content-ID', '<qrcode>')
                    img.add_header('Content-Disposition', 'inline', filename='qr_code.png')
                    msg.attach(img)

            # Send email
            if use_tls:
                server = smtplib.SMTP(mail_server, mail_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(mail_server, mail_port)

            server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()

            current_app.logger.info(f"QR code email sent to {recipient_email}")
            return True, "QR code has been sent to your email!"

        except smtplib.SMTPAuthenticationError:
            current_app.logger.error("SMTP authentication failed")
            return False, "Email service authentication failed. QR code saved to your account."
        except Exception as e:
            current_app.logger.error(f"Email sending error: {e}")
            return False, f"Could not send email. QR code has been saved to your account."

    @staticmethod
    def send_notification(recipient_email, subject, message):
        """Send a generic notification email."""
        try:
            mail_server = current_app.config.get('MAIL_SERVER')
            mail_port = current_app.config.get('MAIL_PORT')
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
            use_tls = current_app.config.get('MAIL_USE_TLS', True)

            if not mail_username or not mail_password:
                return False, "Email not configured."

            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = mail_sender
            msg['To'] = recipient_email
            msg.attach(MIMEText(message, 'html'))

            if use_tls:
                server = smtplib.SMTP(mail_server, mail_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(mail_server, mail_port)

            server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()

            return True, "Notification sent."
        except Exception as e:
            current_app.logger.error(f"Notification email error: {e}")
            return False, str(e)

    @staticmethod
    def send_test_email(recipient_email):
        """
        Send a simple test email (e.g. to verify Brevo SMTP).
        Returns (success: bool, message: str)
        """
        subject = 'Smart Attendance – Brevo test email'
        html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #f8fafc; 
                        border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0;">
                <h2 style="color: #1a1a2e; margin: 0 0 16px;">Brevo test</h2>
                <p style="color: #475569; line-height: 1.6;">
                    This is a test email from the <strong>Smart Student Attendance System</strong>.
                </p>
                <p style="color: #475569;">
                    If you received this, Brevo SMTP is configured correctly.
                </p>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 24px;">
                    Sent to: {recipient_email}
                </p>
            </div>
        </body>
        </html>
        """
        return EmailService.send_notification(recipient_email, subject, html)
