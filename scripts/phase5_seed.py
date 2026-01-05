import sys
sys.path.append('.')
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.modules.users.models import User, UserRole
from app.core.auth.password import hash_password

print("Creating tables with audit...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    users = [
        {"email": "admin@phase5.com", "password": "test123", "role": UserRole.ADMIN},
        {"email": "viewer@phase5.com", "password": "test123", "role": UserRole.VIEWER}
    ]
    
    for u in users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if not existing:
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                is_active=True
            )
            db.add(user)
            print(f"Created: {u['email']} ({u['role']})")
    
    db.commit()
    print("✅ Phase 5 users ready!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
