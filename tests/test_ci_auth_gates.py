"""
CI Gate Tests - Authentication & Authorization
Phase 6: Ensure Auth semantics remain correct across deployments
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db, SessionLocal, engine
from app.db.base import Base
from app.modules.users.models import User, UserRole
from app.core.auth.password import hash_password

# Test client
client = TestClient(app)

# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_users(db_session: Session):
    """Create test users for auth testing."""
    users = {
        "viewer": User(
            email="viewer@test.local",
            hashed_password=hash_password("testpass"),
            role=UserRole.VIEWER,
            is_active=True
        ),
        "staff": User(
            email="staff@test.local", 
            hashed_password=hash_password("testpass"),
            role=UserRole.STAFF,
            is_active=True
        ),
        "admin": User(
            email="admin@test.local",
            hashed_password=hash_password("testpass"),
            role=UserRole.ADMIN,
            is_active=True
        ),
        "inactive": User(
            email="inactive@test.local",
            hashed_password=hash_password("testpass"),
            role=UserRole.VIEWER,
            is_active=False
        )
    }
    
    for user in users.values():
        db_session.add(user)
    db_session.commit()
    
    return users

def get_token(email: str, password: str = "testpass") -> str:
    """Helper to get auth token for user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

class TestAuthenticationGates:
    """CI Gate: Authentication semantics (401) must be correct"""
    
    def test_no_token_returns_401(self, test_users):
        """GATE: No token must return 401 + WWW-Authenticate header"""
        response = client.get("/api/v1/inventory/items")
        
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert "detail" in response.json()
    
    def test_invalid_token_returns_401(self, test_users):
        """GATE: Invalid token must return 401"""
        response = client.get(
            "/api/v1/inventory/items",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_malformed_token_returns_401(self, test_users):
        """GATE: Malformed Authorization header returns 401"""
        response = client.get(
            "/api/v1/inventory/items",
            headers={"Authorization": "NotBearer token"}
        )
        
        assert response.status_code == 401
    
    def test_expired_token_returns_401(self, test_users):
        """GATE: Expired token must return 401 (simulated with invalid signature)"""
        fake_expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.signature"
        
        response = client.get(
            "/api/v1/inventory/items", 
            headers={"Authorization": f"Bearer {fake_expired_token}"}
        )
        
        assert response.status_code == 401
    
    def test_inactive_user_returns_401(self, test_users):
        """GATE: Inactive user must not be able to authenticate"""
        # Try to login with inactive user
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@test.local", "password": "testpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should fail to login or if login succeeds, API calls should fail
        if response.status_code == 200:
            token = response.json()["access_token"]
            api_response = client.get(
                "/api/v1/inventory/items",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert api_response.status_code == 401
        else:
            assert response.status_code == 401

    def test_valid_token_successful_auth(self, test_users):
        """GATE: Valid token with active user succeeds"""
        token = get_token("viewer@test.local")
        assert token is not None
        
        response = client.get(
            "/api/v1/inventory/items",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed (200) or fail with 403 (authorization), but NOT 401
        assert response.status_code in [200, 403]
        assert response.status_code != 401

class TestAuthorizationGates:
    """CI Gate: Authorization semantics (403) must be correct"""
    
    def test_viewer_cannot_post_items(self, test_users):
        """GATE: VIEWER role must get 403 on POST /items"""
        token = get_token("viewer@test.local")
        assert token is not None
        
        response = client.post(
            "/api/v1/inventory/items",
            json={"sku": "TEST-001", "name": "Test Item", "unit": "PCS"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "detail" in response.json()
        assert "not permitted" in response.json()["detail"].lower()
    
    def test_staff_cannot_delete_items(self, test_users):
        """GATE: STAFF role must get 403 on DELETE /items"""
        token = get_token("staff@test.local")
        assert token is not None
        
        response = client.delete(
            "/api/v1/inventory/items/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    def test_admin_can_access_admin_endpoints(self, test_users):
        """GATE: ADMIN role can access admin-protected endpoints"""
        token = get_token("admin@test.local")
        assert token is not None
        
        # Admin should be able to POST items (or get 404/422 for business reasons)
        response = client.post(
            "/api/v1/inventory/items",
            json={"sku": "TEST-001", "name": "Test Item", "unit": "PCS"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should NOT get 401 or 403 (auth/authz errors)
        assert response.status_code not in [401, 403]
    
    def test_viewer_can_read_items(self, test_users):
        """GATE: VIEWER can access read-only endpoints"""
        token = get_token("viewer@test.local")
        assert token is not None
        
        response = client.get(
            "/api/v1/inventory/items",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed
        assert response.status_code == 200

class TestRBACMatrix:
    """CI Gate: RBAC permission matrix must be enforced correctly"""
    
    @pytest.mark.parametrize("role,endpoint,method,expected_status", [
        # VIEWER permissions
        ("viewer", "/api/v1/inventory/items", "GET", 200),
        ("viewer", "/api/v1/inventory/locations", "GET", 200),
        ("viewer", "/api/v1/inventory/stock/current", "GET", 200),
        ("viewer", "/api/v1/inventory/items", "POST", 403),
        ("viewer", "/api/v1/inventory/stock/in", "POST", 403),
        
        # STAFF permissions  
        ("staff", "/api/v1/inventory/items", "GET", 200),
        ("staff", "/api/v1/inventory/stock/in", "POST", [200, 404, 422]),  # Business validation may fail
        ("staff", "/api/v1/inventory/items", "POST", 403),
        ("staff", "/api/v1/inventory/items/1", "DELETE", 403),
        
        # ADMIN permissions
        ("admin", "/api/v1/inventory/items", "GET", 200),
        ("admin", "/api/v1/inventory/items", "POST", [200, 409, 422]),  # May fail business validation
        ("admin", "/api/v1/inventory/items/1", "PUT", [200, 404]),  # May not exist
        ("admin", "/api/v1/inventory/items/1", "DELETE", [200, 404]),  # May not exist
    ])
    def test_rbac_matrix_enforcement(self, test_users, role, endpoint, method, expected_status):
        """GATE: RBAC matrix must be enforced per specification"""
        token = get_token(f"{role}@test.local")
        assert token is not None
        
        headers = {"Authorization": f"Bearer {token}"}
        
        if method == "GET":
            response = client.get(endpoint, headers=headers)
        elif method == "POST":
            # Use minimal valid payload for POST requests
            if "items" in endpoint:
                response = client.post(endpoint, json={"sku": "TEST", "name": "Test", "unit": "PCS"}, headers=headers)
            elif "stock" in endpoint:
                response = client.post(endpoint, json={"item_id": 1, "location_id": 1, "quantity": 1}, headers=headers)
            else:
                response = client.post(endpoint, json={}, headers=headers)
        elif method == "PUT":
            response = client.put(endpoint, json={"name": "Updated"}, headers=headers)
        elif method == "DELETE":
            response = client.delete(endpoint, headers=headers)
        
        # Check status code matches expected
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status

class TestEndpointSecurityCoverage:
    """CI Gate: All endpoints must have proper auth protection"""
    
    def test_all_inventory_endpoints_require_auth(self):
        """GATE: All inventory endpoints must require authentication"""
        inventory_endpoints = [
            "/api/v1/inventory/items",
            "/api/v1/inventory/locations", 
            "/api/v1/inventory/stock/current",
            "/api/v1/inventory/stock/ledger",
            "/api/v1/inventory/audit"
        ]
        
        for endpoint in inventory_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} must require authentication"
    
    def test_sensitive_endpoints_require_admin_auth(self):
        """GATE: Sensitive endpoints require ADMIN+ authorization"""
        # Get VIEWER token
        viewer_token = get_token("viewer@test.local") 
        
        sensitive_endpoints = [
            ("/api/v1/inventory/items", "POST"),
            ("/api/v1/inventory/items/1", "PUT"),
            ("/api/v1/inventory/items/1", "DELETE"),
            ("/api/v1/inventory/audit", "GET")
        ]
        
        for endpoint, method in sensitive_endpoints:
            headers = {"Authorization": f"Bearer {viewer_token}"}
            
            if method == "POST":
                response = client.post(endpoint, json={"sku": "TEST", "name": "Test"}, headers=headers)
            elif method == "PUT":
                response = client.put(endpoint, json={"name": "Test"}, headers=headers) 
            elif method == "DELETE":
                response = client.delete(endpoint, headers=headers)
            elif method == "GET":
                response = client.get(endpoint, headers=headers)
            
            assert response.status_code == 403, f"{method} {endpoint} must require ADMIN+ role"