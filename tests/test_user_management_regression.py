"""
Critical Regression Tests for User Management
These tests prevent the "fix then revert" problem by testing the complete user lifecycle
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

class TestUserLifecycleRegression:
    """Critical tests to prevent user management regressions"""
    
    def test_complete_user_lifecycle_e2e(self, client: TestClient, db_session: Session, auth_tokens):
        """
        CRITICAL: End-to-end user lifecycle test
        This test prevents regression by validating the complete flow:
        Admin creates user → User can login → Admin disables user → User cannot login → Admin enables → User can login
        """
        admin_token = auth_tokens.get("admin")
        
        # Step 1: Admin creates a new user
        new_user_data = {
            "email": "lifecycle_test@test.com",
            "password": "testpassword123",
            "role": "staff"
        }
        
        create_response = client.post(
            "/api/v1/users/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=new_user_data
        )
        
        assert create_response.status_code == 201, f"User creation failed: {create_response.text}"
        created_user = create_response.json()
        user_id = created_user["id"]
        assert created_user["email"] == new_user_data["email"]
        assert created_user["role"] == new_user_data["role"]
        assert created_user["is_active"] is True
        
        # Step 2: New user can login successfully
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": new_user_data["email"], "password": new_user_data["password"]}
        )
        
        assert login_response.status_code == 200, f"New user login failed: {login_response.text}"
        user_token = login_response.json()["access_token"]
        assert user_token is not None
        
        # Step 3: New user can access /auth/me
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert me_response.status_code == 200, f"/auth/me failed: {me_response.text}"
        user_profile = me_response.json()
        assert user_profile["email"] == new_user_data["email"]
        assert user_profile["is_active"] is True
        
        # Step 4: Admin disables the user
        disable_response = client.delete(
            f"/api/v1/users/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert disable_response.status_code == 200, f"User disable failed: {disable_response.text}"
        disable_result = disable_response.json()
        assert disable_result["message"] == "User disabled successfully"
        
        # Step 5: Disabled user cannot login  
        login_disabled_response = client.post(
            "/api/v1/auth/login",
            data={"username": new_user_data["email"], "password": new_user_data["password"]}
        )
        
        assert login_disabled_response.status_code == 401, f"Disabled user should not be able to login: {login_disabled_response.text}"
        error_detail = login_disabled_response.json()["detail"]
        assert "inactive" in error_detail.lower() or "disabled" in error_detail.lower()
        
        # Step 6: Admin re-enables the user
        enable_response = client.put(
            f"/api/v1/users/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": True}
        )
        
        assert enable_response.status_code == 200, f"User re-enable failed: {enable_response.text}"
        enabled_user = enable_response.json()
        assert enabled_user["is_active"] is True
        
        # Step 7: Re-enabled user can login again
        login_reenabled_response = client.post(
            "/api/v1/auth/login",
            data={"username": new_user_data["email"], "password": new_user_data["password"]}
        )
        
        assert login_reenabled_response.status_code == 200, f"Re-enabled user login failed: {login_reenabled_response.text}"
        new_token = login_reenabled_response.json()["access_token"]
        assert new_token is not None
        
        # Step 8: Re-enabled user can access protected endpoints
        final_me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        assert final_me_response.status_code == 200, f"Re-enabled user /auth/me failed: {final_me_response.text}"
        final_profile = final_me_response.json()
        assert final_profile["email"] == new_user_data["email"]
        assert final_profile["is_active"] is True
        
        print("✅ CRITICAL: Complete user lifecycle test PASSED")

    def test_role_escalation_prevention(self, client: TestClient, auth_tokens):
        """
        CRITICAL: Prevents role escalation vulnerabilities
        Ensures ADMIN users cannot create SUPER_ADMIN users
        """
        # Create a regular ADMIN user first (not the test SUPER_ADMIN)
        super_admin_token = auth_tokens.get("admin")  # This is actually SUPER_ADMIN
        
        admin_user_data = {
            "email": "regular_admin@test.com",
            "password": "adminpassword123", 
            "role": "admin"
        }
        
        create_admin_response = client.post(
            "/api/v1/users/users",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=admin_user_data
        )
        
        assert create_admin_response.status_code == 201
        
        # Login as the new ADMIN user
        admin_login_response = client.post(
            "/api/v1/auth/login",
            data={"username": admin_user_data["email"], "password": admin_user_data["password"]}
        )
        
        assert admin_login_response.status_code == 200
        regular_admin_token = admin_login_response.json()["access_token"]
        
        # Regular ADMIN tries to create SUPER_ADMIN user (should fail)
        superadmin_attempt_data = {
            "email": "hacker@test.com",
            "password": "hackerpassword123",
            "role": "super_admin"
        }
        
        escalation_response = client.post(
            "/api/v1/users/users",
            headers={"Authorization": f"Bearer {regular_admin_token}"},
            json=superadmin_attempt_data
        )
        
        assert escalation_response.status_code == 403, f"Role escalation should be prevented: {escalation_response.text}"
        assert "only super_admin" in escalation_response.json()["detail"].lower()
        
        print("✅ CRITICAL: Role escalation prevention test PASSED")

    def test_self_disable_prevention(self, client: TestClient, auth_tokens):
        """
        CRITICAL: Prevents users from disabling themselves
        This prevents lockout scenarios
        """
        admin_token = auth_tokens.get("admin")
        
        # Get admin user ID by calling /auth/me
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert me_response.status_code == 200
        admin_user_id = me_response.json()["id"]
        
        # Try to disable own account (should fail)
        self_disable_response = client.delete(
            f"/api/v1/users/users/{admin_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert self_disable_response.status_code == 400, f"Self-disable should be prevented: {self_disable_response.text}"
        assert "cannot disable your own account" in self_disable_response.json()["detail"].lower()
        
        print("✅ CRITICAL: Self-disable prevention test PASSED")

    def test_password_validation_enforcement(self, client: TestClient, auth_tokens):
        """
        CRITICAL: Ensures password validation is consistently enforced
        """
        admin_token = auth_tokens.get("admin")
        
        # Test password too short
        weak_password_data = {
            "email": "weak_password@test.com",
            "password": "123",  # Too short
            "role": "staff"
        }
        
        weak_response = client.post(
            "/api/v1/users/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=weak_password_data
        )
        
        assert weak_response.status_code == 400, f"Weak password should be rejected: {weak_response.text}"
        assert "8 characters" in weak_response.json()["detail"].lower()
        
        print("✅ CRITICAL: Password validation test PASSED")

    def test_database_consistency_check(self, client: TestClient, db_session: Session, auth_tokens):
        """
        CRITICAL: Verifies database operations are properly committed
        Prevents the "works in API but not in DB" issue
        """
        from app.modules.users.models import User
        
        admin_token = auth_tokens.get("admin")
        
        # Create user via API
        test_user_data = {
            "email": "db_consistency@test.com",
            "password": "password123",
            "role": "staff"
        }
        
        api_response = client.post(
            "/api/v1/users/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=test_user_data
        )
        
        assert api_response.status_code == 201
        api_user = api_response.json()
        
        # Verify user exists directly in database
        db_user = db_session.query(User).filter(User.email == test_user_data["email"]).first()
        assert db_user is not None, "User should exist in database after API creation"
        assert db_user.email == test_user_data["email"]
        assert db_user.role.value == test_user_data["role"]
        assert db_user.is_active is True
        
        # Disable user via API
        disable_response = client.delete(
            f"/api/v1/users/users/{api_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert disable_response.status_code == 200
        
        # Verify disable is committed to database
        db_session.refresh(db_user)
        assert db_user.is_active is False, "User should be disabled in database after API disable"
        
        print("✅ CRITICAL: Database consistency test PASSED")


def test_deterministic_behavior(client: TestClient, auth_tokens):
    """
    CRITICAL: Ensures all operations are deterministic
    Run this test 3 times - should pass identically each time
    """
    admin_token = auth_tokens.get("admin")
    
    # Test user list consistency 
    response1 = client.get(
        "/api/v1/users/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    response2 = client.get(
        "/api/v1/users/users", 
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response1.status_code == response2.status_code == 200
    users1 = response1.json()
    users2 = response2.json()
    
    # Results should be identical
    assert len(users1) == len(users2), "User list should be deterministic"
    assert users1 == users2, "User list should be identical on repeated calls"
    
    print("✅ CRITICAL: Deterministic behavior test PASSED")