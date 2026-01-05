#!/usr/bin/env python3
"""
Script to create an admin user for the SME ERP system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.modules.users.models import User, UserRole
from app.core.auth.security import hash_password

def create_admin_user():
    """Create an admin user if it doesn't exist."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.email == "admin@sme-erp.com").first()
        
        if admin_user:
            print("Admin user already exists!")
            print(f"Email: {admin_user.email}")
            print(f"Role: {admin_user.role}")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@sme-erp.com",
            hashed_password=hash_password("admin123"),
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print("📧 Email: admin@sme-erp.com")
        print("🔑 Password: admin123")
        print("👑 Role: SUPER_ADMIN")
        print("⚠️  Please change the password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()