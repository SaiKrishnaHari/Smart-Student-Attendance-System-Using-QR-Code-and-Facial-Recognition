"""
Resend QR code email to existing students
"""
import sys
sys.path.insert(0, '.')

from app import app
from models.models import db, User
from services.email_service import EmailService

with app.app_context():
    # Get all students who have QR codes but might not have received emails
    students = User.query.filter(
        User.role == 'student',
        User.qr_code_path.isnot(None)
    ).all()
    
    if not students:
        print("No students found with QR codes.")
    else:
        print(f"Found {len(students)} student(s) with QR codes.\n")
        
        email_service = EmailService()
        
        for student in students:
            print(f"Student: {student.full_name} ({student.email})")
            print(f"  QR Code: {student.qr_code_path}")
            
            # Ask for confirmation
            send = input(f"  Send QR code email to {student.email}? (y/n): ").strip().lower()
            
            if send == 'y':
                success, message = email_service.send_qr_email(
                    student.email,
                    student.full_name,
                    student.qr_code_path
                )
                
                if success:
                    print(f"  ✓ {message}\n")
                else:
                    print(f"  ✗ {message}\n")
            else:
                print("  Skipped.\n")
        
        print("Done!")
