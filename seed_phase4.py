#!/usr/bin/env python3
"""Seed test users and test data for Phase 4"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.modules.users.models import User, UserRole
from app.core.auth.password import hash_password

def seed_all():
    # Create tables
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Seed users
        test_users = [
            {"email": "viewer@test.com", "password": "test123", "role": UserRole.VIEWER},
            {"email": "staff@test.com", "password": "test123", "role": UserRole.STAFF}, 
            {"email": "admin@test.com", "password": "test123", "role": UserRole.ADMIN},
            {"email": "superadmin@test.com", "password": "test123", "role": UserRole.SUPER_ADMIN}
        ]
        
        for user_data in test_users:
            # Check if user exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"User {user_data['email']} already exists")
                continue
                
            # Create user without updated_at initially
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            print(f"Created user: {user_data['email']} with role {user_data['role']}")
            
        db.commit()
        print("✅ All users seeded!")
        
        # Show users
        users = db.query(User).all()
        print(f"\nTotal users: {len(users)}")
        for user in users:
            print(f"  - {user.email}: {user.role}")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Phase 4: Seeding database...")
    seed_all()