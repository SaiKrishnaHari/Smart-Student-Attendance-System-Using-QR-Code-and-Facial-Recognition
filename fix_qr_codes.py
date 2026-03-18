"""
Fix QR codes for existing users with None public_id
"""
import sys
sys.path.insert(0, '.')

from app import app
from models.models import db, User
from services.qr_service import QRService

with app.app_context():
    # Find users with broken QR tokens (containing "None:")
    users = User.query.filter(User.qr_token.like('None:%')).all()
    
    if not users:
        print("No users with broken QR codes found.")
    else:
        print(f"Found {len(users)} user(s) with broken QR codes. Fixing...")
        
        qr_service = QRService()
        for user in users:
            print(f"  Fixing QR for: {user.full_name} (ID: {user.student_id})")
            
            # Generate new QR token with proper public_id
            qr_token = qr_service.generate_qr_token(user.student_id, user.public_id)
            user.qr_token = qr_token
            
            # Generate new QR image
            qr_path, qr_filename = qr_service.generate_qr_image(qr_token, user.full_name)
            if qr_path:
                user.qr_code_path = qr_path
                print(f"    ✓ New QR code generated: {qr_filename}")
            
        db.session.commit()
        print(f"\n✓ Fixed {len(users)} QR code(s) successfully!")
