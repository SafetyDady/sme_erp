import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import get_db
from app.db.base import Base
from app.modules.users.models import User, UserRole
from app.core.auth.password import get_password_hash

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def db_session():
    """Database session"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")  
def test_users(db_session):
    """Create test users with different roles"""
    users_data = [
        {
            "email": "admin@test.com", 
            "role": UserRole.SUPER_ADMIN,
            "password": "admin123"
        },
        {
            "email": "staff@test.com",
            "role": UserRole.STAFF, 
            "password": "staff123"
        },
        {
            "email": "viewer@test.com",
            "role": UserRole.VIEWER,
            "password": "viewer123"
        }
    ]
    
    created_users = []
    for user_data in users_data:
        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            role=user_data["role"],
            is_active=True
        )
        db_session.add(user)
        created_users.append(user)
    
    db_session.commit()
    return created_users

@pytest.fixture
def auth_tokens(client, test_users):
    """Get auth tokens for test users"""
    tokens = {}
    
    login_data = [
        ("admin@test.com", "admin123", "admin"),
        ("staff@test.com", "staff123", "staff"), 
        ("viewer@test.com", "viewer123", "viewer")
    ]
    
    for email, password, role in login_data:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            token_data = response.json()
            tokens[role] = token_data["access_token"]
    
    return tokens