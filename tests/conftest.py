# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

def pytest_configure(config):
    """Configure pytest environment variables."""
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-do-not-use-in-production-very-long-key-minimum-256-bits"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ENVIRONMENT"] = "test"

from app.main import app
from app.db.base import Base

# NOTE: Adjust these imports ONLY if paths differ in this repo.
from app.db.session import get_db  # production dependency to override


TEST_DB_FILE = "test_db.sqlite"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture(scope="session")
def engine():
    # Create a clean DB file once per test session
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    eng = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=eng)

    yield eng

    eng.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """
    Transaction-per-test with nested SAVEPOINT.
    Ensures deterministic DB state even if app code calls commit().
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        # If the nested transaction ended, restart it
        if trans.nested and not trans._parent.nested:
            connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """
    FastAPI TestClient with DB dependency override.
    Must yield the SAME db_session for the whole test.
    """
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def test_users(db_session: Session):
    """
    Seed deterministic users without committing.
    Uses flush() so objects get IDs, and rollback cleans everything.
    """
    # NOTE: Adjust model import paths ONLY if repo differs.
    from app.modules.users.models import User, UserRole
    from app.core.auth.password import get_password_hash

    users_data = [
        ("admin@company.com", "admin123", UserRole.SUPER_ADMIN),
        ("staff@company.com", "staff123", UserRole.STAFF),
        ("viewer@company.com", "viewer123", UserRole.VIEWER),
    ]

    created = []
    for email, password, role in users_data:
        u = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db_session.add(u)
        created.append(u)

    db_session.flush()  # DO NOT commit
    return created


@pytest.fixture(scope="function")
def auth_tokens(client, test_users):
    """
    Login real endpoint to obtain JWT tokens.
    If any token is None, tests must handle it or xfail explicitly.
    """
    tokens = {}
    login_data = [
        ("admin@company.com", "admin123", "admin"),
        ("staff@company.com", "staff123", "staff"),
        ("viewer@company.com", "viewer123", "viewer"),
    ]

    for email, password, role in login_data:
        r = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        tokens[role] = r.json().get("access_token") if r.status_code == 200 else None

    return tokens


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


@pytest.fixture(scope="function")
def as_user(test_users):
    """
    Context manager to override get_current_user safely.
    Must pop only the override it sets.
    """
    # NOTE: Adjust dependency import path ONLY if repo differs.
    from app.core.auth.dependencies import get_current_user

    class Ctx:
        def __init__(self, user):
            self.user = user

        def __enter__(self):
            app.dependency_overrides[get_current_user] = lambda: self.user
            return self.user

        def __exit__(self, exc_type, exc, tb):
            app.dependency_overrides.pop(get_current_user, None)

    def _as_user(user):
        return Ctx(user)

    return _as_user
