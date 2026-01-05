#!/usr/bin/env python3
"""Seed test users for RBAC validation"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from app.db.session import SessionLocal, engine
from app.modules.users.models import User, UserRole, Base
from app.core.auth.password import hash_password

def seed_users():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        test_users = [
            {"email": "viewer@test.com", "password": "test123", "role": UserRole.VIEWER},
            {"email": "staff@test.com", "password": "test123", "role": UserRole.STAFF}, 
            {"email": "admin@test.com", "password": "test123", "role": UserRole.ADMIN},
            {"email": "superadmin@test.com", "password": "test123", "role": UserRole.SUPER_ADMIN}
        ]
        
        for user_data in test_users:
            # Check if user already exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"User {user_data['email']} already exists, skipping...")
                continue
                
            # Create new user
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            print(f"Created user: {user_data['email']} with role {user_data['role']}")
            
        db.commit()
        print("✅ All test users seeded successfully!")
        
        # Verify users
        users = db.query(User).all()
        print(f"\nTotal users in database: {len(users)}")
        for user in users:
            print(f"  - {user.email}: {user.role}")
            
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Seeding test users...")
    seed_users()