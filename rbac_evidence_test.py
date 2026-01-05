#!/usr/bin/env python3
"""
Phase 8 Task 2: CRUD Users RBAC Evidence Testing
Tests all CRUD operations with different roles to prove RBAC correctness
"""

import json
import requests
import sys
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class RBACTester:
    def __init__(self):
        self.tokens = {}
        self.users = {}
        self.test_results = []
        
    def log_result(self, test_name: str, expected: str, actual: int, passed: bool):
        """Log test result"""
        result = {
            "test": test_name,
            "expected": expected, 
            "actual_status": actual,
            "passed": passed
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: Expected {expected}, Got {actual}")
        
    def create_test_user(self, email: str, password: str, role: str) -> Dict[str, Any]:
        """Create a test user and get auth token"""
        try:
            # Login to get token (assume user exists from seed)
            login_data = {"username": email, "password": password}
            response = requests.post(f"{API_BASE}/auth/login", data=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.tokens[role] = token_data["access_token"]
                
                # Get user info
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                user_response = requests.get(f"{API_BASE}/users/current-user", headers=headers)
                if user_response.status_code == 200:
                    self.users[role] = user_response.json()
                    print(f"✅ {role} user ready: {email}")
                    return user_response.json()
            
            print(f"❌ Failed to setup {role} user: {email}")
            return None
            
        except Exception as e:
            print(f"❌ Error setting up {role} user: {e}")
            return None
    
    def test_endpoint(self, method: str, endpoint: str, role: str, expected_status: int, 
                     data: Dict = None, description: str = ""):
        """Test an endpoint with specific role and expected status"""
        try:
            headers = {"Authorization": f"Bearer {self.tokens[role]}"} if role in self.tokens else {}
            
            if method == "GET":
                response = requests.get(f"{API_BASE}{endpoint}", headers=headers)
            elif method == "POST":
                response = requests.post(f"{API_BASE}{endpoint}", headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(f"{API_BASE}{endpoint}", headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(f"{API_BASE}{endpoint}", headers=headers)
            
            test_name = f"{method} {endpoint} as {role.upper()}"
            if description:
                test_name += f" - {description}"
                
            passed = response.status_code == expected_status
            expected_desc = f"{expected_status} ({'ALLOW' if expected_status < 400 else 'DENY'})"
            
            self.log_result(test_name, expected_desc, response.status_code, passed)
            
            # Return response for further testing
            return response
            
        except Exception as e:
            print(f"❌ Error testing {method} {endpoint} as {role}: {e}")
            return None
    
    def run_rbac_evidence_tests(self):
        """Run comprehensive RBAC evidence tests"""
        print("🧪 Starting RBAC Evidence Testing for CRUD Users")
        print("=" * 60)
        
        # Test 1: Authentication required (401 without token)
        print("\n📋 Test Group 1: Authentication Required")
        self.test_endpoint("GET", "/users/users", "none", 401, description="No auth token")
        self.test_endpoint("GET", "/users/roles", "none", 401, description="No auth token") 
        self.test_endpoint("POST", "/users/users", "none", 401, description="No auth token")
        
        # Test 2: VIEWER permissions (403 for CRUD operations)
        print("\n📋 Test Group 2: VIEWER Role Restrictions")
        if "viewer" in self.tokens:
            self.test_endpoint("GET", "/users/users", "viewer", 403, description="List users")
            self.test_endpoint("GET", "/users/roles", "viewer", 403, description="List roles")
            self.test_endpoint("POST", "/users/users", "viewer", 403, 
                             data={"email": "test@example.com", "password": "password123", "role": "viewer"},
                             description="Create user")
        
        # Test 3: STAFF permissions (403 for user management)
        print("\n📋 Test Group 3: STAFF Role Restrictions")
        if "staff" in self.tokens:
            self.test_endpoint("GET", "/users/users", "staff", 403, description="List users")
            self.test_endpoint("GET", "/users/roles", "staff", 403, description="List roles")
            self.test_endpoint("POST", "/users/users", "staff", 403,
                             data={"email": "test@example.com", "password": "password123", "role": "viewer"},
                             description="Create user")
        
        # Test 4: ADMIN permissions (200 for most operations)
        print("\n📋 Test Group 4: ADMIN Role Permissions")
        if "admin" in self.tokens:
            self.test_endpoint("GET", "/users/users", "admin", 200, description="List users")
            self.test_endpoint("GET", "/users/roles", "admin", 200, description="List roles")
            self.test_endpoint("GET", "/users/current-user", "admin", 200, description="Current user")
            
            # ADMIN cannot reset passwords (403)
            if "viewer" in self.users:
                viewer_id = self.users["viewer"]["id"]
                self.test_endpoint("POST", f"/users/users/{viewer_id}/reset-password?new_password=newpass123",
                                 "admin", 403, description="Reset password (should fail)")
                                 
            # ADMIN cannot create SUPER_ADMIN users (403)
            self.test_endpoint("POST", "/users/users", "admin", 403,
                             data={"email": "newsuperadmin@test.com", "password": "password123", "role": "super_admin"},
                             description="Create SUPER_ADMIN user (should fail)")
                             
        # Test 5: SUPER_ADMIN permissions (200 for all operations)
        print("\n📋 Test Group 5: SUPER_ADMIN Full Permissions")
        if "super_admin" in self.tokens:
            self.test_endpoint("GET", "/users/users", "super_admin", 200, description="List users")
            self.test_endpoint("GET", "/users/roles", "super_admin", 200, description="List roles")
            
            # SUPER_ADMIN can reset passwords (200)
            if "viewer" in self.users:
                viewer_id = self.users["viewer"]["id"]
                self.test_endpoint("POST", f"/users/users/{viewer_id}/reset-password?new_password=newpass123",
                                 "super_admin", 200, description="Reset password (should work)")
            
            # SUPER_ADMIN can create any role (201)
            self.test_endpoint("POST", "/users/users", "super_admin", 201,
                             data={"email": "testadmin@test.com", "password": "password123", "role": "admin"},
                             description="Create ADMIN user (should work)")
        
        # Test 6: Safety checks
        print("\n📋 Test Group 6: Safety Protection Checks")
        if "admin" in self.tokens and "admin" in self.users:
            admin_id = self.users["admin"]["id"]
            # Cannot disable yourself (400)
            self.test_endpoint("DELETE", f"/users/users/{admin_id}", "admin", 400, 
                             description="Self-disable protection")
        
        # Test 7: Duplicate email prevention
        print("\n📋 Test Group 7: Email Uniqueness")
        if "admin" in self.tokens and "viewer" in self.users:
            viewer_email = self.users["viewer"]["email"]
            self.test_endpoint("POST", "/users/users", "admin", 409,
                             data={"email": viewer_email, "password": "password123", "role": "viewer"},
                             description="Duplicate email prevention")
        
        print("\n" + "=" * 60)
        self.print_summary()
        
    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"🧪 RBAC Evidence Test Summary:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed} ✅")
        print(f"   Failed: {failed} ❌")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   - {result['test']}")
        else:
            print(f"\n🎉 All RBAC tests passed! User CRUD APIs are properly secured.")

def main():
    """Main test execution"""
    print("🚀 Phase 8 Task 2: CRUD Users RBAC Evidence")
    print("Testing RBAC correctness for User Management APIs")
    print()
    
    tester = RBACTester()
    
    # Setup test users (assume they exist from seeding)
    print("📋 Setting up test users...")
    test_users = [
        ("viewer@test.com", "password123", "viewer"),
        ("staff@test.com", "password123", "staff"), 
        ("admin@test.com", "password123", "admin"),
        ("super@test.com", "password123", "super_admin")
    ]
    
    for email, password, role in test_users:
        tester.create_test_user(email, password, role)
    
    print()
    
    # Run evidence tests
    tester.run_rbac_evidence_tests()

if __name__ == "__main__":
    main()