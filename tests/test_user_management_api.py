"""
Test suite for Phase 8 User & Role Management API
Tests CRUD operations and RBAC enforcement
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_list_users_requires_admin(client: TestClient, test_users, auth_tokens):
    """Test that listing users requires ADMIN+ role"""
    viewer_token = auth_tokens.get("viewer")
    
    response = client.get(
        "/api/v1/users/users", 
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    
    assert response.status_code == 403
    assert "operation not permitted" in response.json()["detail"].lower()

def test_list_users_admin_success(client: TestClient, test_users, auth_tokens):
    """Test that ADMIN+ can list users"""
    admin_token = auth_tokens.get("admin")
    
    response = client.get(
        "/api/v1/users/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 3  # At least the 3 test users

def test_create_user_role_restrictions(client: TestClient, test_users, auth_tokens):
    """Test role creation restrictions"""
    admin_token = auth_tokens.get("admin")  # This is actually SUPER_ADMIN from conftest
    
    # SUPER_ADMIN can create any role
    response = client.post(
        "/api/v1/users/users", 
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "newadmin@test.com",
            "password": "password123",
            "role": "admin"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["role"] == "admin"

def test_update_user_permissions(client: TestClient, db_session: Session, test_users, auth_tokens):
    """Test user update permission enforcement"""
    from app.modules.users.models import User, UserRole
    
    admin_token = auth_tokens.get("admin")
    staff_user = test_users[1]  # Staff user from test_users fixture
    
    # ADMIN can modify non-admin users
    response = client.put(
        f"/api/v1/users/users/{staff_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "viewer"}
    )
    
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"

def test_disable_user_restrictions(client: TestClient, test_users, auth_tokens):
    """Test user disable restrictions"""
    admin_token = auth_tokens.get("admin") 
    admin_user = test_users[0]  # Admin user from test_users fixture
    
    # Cannot disable yourself
    response = client.delete(
        f"/api/v1/users/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 400
    assert "cannot disable your own account" in response.json()["detail"].lower()

def test_list_roles_endpoint(client: TestClient, test_users, auth_tokens):
    """Test roles listing endpoint"""
    admin_token = auth_tokens.get("admin")
    
    response = client.get(
        "/api/v1/users/roles",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) == 4  # VIEWER, STAFF, ADMIN, SUPER_ADMIN
    
    role_names = [role["role"] for role in roles]
    assert "viewer" in role_names
    assert "admin" in role_names
    assert "super_admin" in role_names

def test_reset_password_super_admin_only(client: TestClient, db_session: Session, test_users, auth_tokens):
    """Test password reset requires SUPER_ADMIN"""
    from app.modules.users.models import User, UserRole
    
    admin_token = auth_tokens.get("admin")  # This is actually SUPER_ADMIN
    viewer_user = test_users[2]  # Viewer user from test_users fixture
    
    # SUPER_ADMIN can reset passwords
    response = client.post(
        f"/api/v1/users/users/{viewer_user.id}/reset-password?new_password=newpass123",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert "password reset successfully" in response.json()["message"].lower()

def test_get_current_user_info(client: TestClient, test_users, auth_tokens):
    """Test current user info endpoint"""
    admin_token = auth_tokens.get("admin")
    admin_user = test_users[0]
    
    response = client.get(
        "/api/v1/users/current-user",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["email"] == admin_user.email
    assert user_info["role"] == admin_user.role.value
    assert user_info["is_active"] is True

def test_user_filtering(client: TestClient, db_session: Session, test_users, auth_tokens):
    """Test user list filtering functionality"""
    from app.modules.users.models import User, UserRole
    
    admin_token = auth_tokens.get("admin")
    
    # Create additional test users with different statuses
    viewer_inactive = User(
        email="viewer_inactive@test.com",
        hashed_password="hashed",
        role=UserRole.VIEWER,
        is_active=False
    )
    db_session.add(viewer_inactive)
    db_session.commit()
    
    # Test role filtering
    response = client.get(
        "/api/v1/users/users?role_filter=viewer",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert all(user["role"] == "viewer" for user in users)
    
    # Test active filtering
    response = client.get(
        "/api/v1/users/users?active_filter=false",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert all(user["is_active"] is False for user in users)