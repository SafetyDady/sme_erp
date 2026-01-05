#!/usr/bin/env python3
from app.core.db import get_db
from app.models.users import User, UserRole
from app.core.auth.password import get_password_hash

def create_test_users():
    db = next(get_db())
    
    # Test users for RBAC matrix testing
    test_users = [
        {"email": "admin@test.com", "role": UserRole.SUPER_ADMIN, "password": "admin123"},
        {"email": "staff@test.com", "role": UserRole.STAFF, "password": "staff123"},  
        {"email": "viewer@test.com", "role": UserRole.VIEWER, "password": "viewer123"}
    ]
    
    for user_data in test_users:
        # Check if user exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            print(f"✅ Created {user_data['role'].value}: {user_data['email']}")
        else:
            print(f"⚠️  Already exists: {user_data['email']} ({existing.role.value})")
    
    db.commit()
    db.close()
    print("🎯 Test users ready for RBAC validation")

if __name__ == "__main__":
    create_test_users()
