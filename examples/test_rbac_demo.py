#!/usr/bin/env python3
"""
Test script for RBAC (Role-Based Access Control) in Inventory API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8002"

# Test users with different roles
USERS = {
    "admin": {"username": "admin@sme-erp.com", "password": "admin123", "expected_role": "SUPER_ADMIN"},
    "staff": {"username": "staff@sme-erp.com", "password": "staff123", "expected_role": "STAFF"},  
    "viewer": {"username": "viewer@sme-erp.com", "password": "viewer123", "expected_role": "VIEWER"}
}

def test_endpoint(method, url, data=None, headers=None, description="", expect_status=200):
    try:
        print(f"\n🧪 {description}")
        print(f"   {method} {url}")

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if isinstance(data, dict):
                response = requests.post(url, json=data, headers=headers)
            else:
                response = requests.post(url, data=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)

        print(f"   Status: {response.status_code} (expected: {expect_status})")
        
        success = response.status_code == expect_status
        if success:
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")

        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                result = response.json()
                if success or response.status_code in [401, 403]:
                    print(f"   Response: {json.dumps(result, indent=2)}")
                return result
            except:
                print(f"   Response: {response.text}")
                return response.text
        else:
            print(f"   Response: {response.text}")
            return response.text

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def login_and_get_token(user_type):
    """Login and get access token for a specific user type"""
    if user_type not in USERS:
        print(f"Unknown user type: {user_type}")
        return None
        
    user_data = USERS[user_type]
    # Use form data for OAuth2PasswordRequestForm
    login_data = f"username={user_data['username']}&password={user_data['password']}"
    
    try:
        print(f"\n🧪 Login as {user_type}")
        print(f"   POST {BASE_URL}/api/v1/auth/login")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            token = result["access_token"]
            print(f"   ✅ Got {user_type} token: {token[:30]}...")
            return token
        else:
            print(f"   ❌ Failed to get {user_type} token: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error logging in as {user_type}: {e}")
        return None

def test_rbac_policies():
    print("🔐 Testing RBAC Policies for Inventory API\n")
    
    # Get tokens for all user types
    tokens = {}
    for user_type in USERS.keys():
        tokens[user_type] = login_and_get_token(user_type)
        if not tokens[user_type]:
            print(f"Failed to get token for {user_type}, skipping RBAC tests")
            return

    print("\n" + "="*60)
    print("🔍 Testing VIEWER permissions (read-only)")
    print("="*60)
    
    viewer_headers = {"Authorization": f"Bearer {tokens['viewer']}"}
    
    # VIEWER should be able to GET items and stock
    test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/items", 
                 headers=viewer_headers, description="VIEWER: Get inventory items", expect_status=200)
    
    test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/stock", 
                 headers=viewer_headers, description="VIEWER: Get stock levels", expect_status=200)
    
    # VIEWER should NOT be able to POST/PUT/DELETE
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/items", 
                 data={"name": "Test Item", "quantity": 5, "price": 100}, 
                 headers=viewer_headers, description="VIEWER: Create item (should fail)", expect_status=403)
    
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/tx", 
                 data={"item_id": 1, "quantity": 5, "type": "in"}, 
                 headers=viewer_headers, description="VIEWER: Create transaction (should fail)", expect_status=403)

    print("\n" + "="*60)
    print("⚙️ Testing STAFF permissions (read + write)")
    print("="*60)
    
    staff_headers = {"Authorization": f"Bearer {tokens['staff']}"}
    
    # STAFF should be able to read 
    test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/items", 
                 headers=staff_headers, description="STAFF: Get inventory items", expect_status=200)
    
    # STAFF should be able to create items and transactions
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/items", 
                 data={"name": "Staff Item", "quantity": 10, "price": 500}, 
                 headers=staff_headers, description="STAFF: Create item", expect_status=200)
    
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/tx", 
                 data={"item_id": 1, "quantity": 3, "type": "out", "notes": "Staff transaction"}, 
                 headers=staff_headers, description="STAFF: Create transaction", expect_status=200)
    
    # STAFF should NOT be able to create locations or delete items  
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/locations", 
                 data={"name": "Unauthorized Location", "address": "Somewhere"}, 
                 headers=staff_headers, description="STAFF: Create location (should fail)", expect_status=403)
    
    test_endpoint("DELETE", f"{BASE_URL}/api/v1/inventory/items/1", 
                 headers=staff_headers, description="STAFF: Delete item (should fail)", expect_status=403)

    print("\n" + "="*60)
    print("🛡️ Testing ADMIN permissions (full access)")
    print("="*60)
    
    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    
    # ADMIN should be able to do everything
    test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/items", 
                 headers=admin_headers, description="ADMIN: Get inventory items", expect_status=200)
    
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/items", 
                 data={"name": "Admin Item", "quantity": 15, "price": 1000}, 
                 headers=admin_headers, description="ADMIN: Create item", expect_status=200)
    
    test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/locations", 
                 data={"name": "Admin Warehouse", "address": "Admin City"}, 
                 headers=admin_headers, description="ADMIN: Create location", expect_status=200)
    
    test_endpoint("PUT", f"{BASE_URL}/api/v1/inventory/items/1", 
                 data={"name": "Updated Item", "quantity": 20, "price": 2000}, 
                 headers=admin_headers, description="ADMIN: Update item", expect_status=200)
    
    test_endpoint("DELETE", f"{BASE_URL}/api/v1/inventory/items/1", 
                 headers=admin_headers, description="ADMIN: Delete item", expect_status=200)

def main():
    print("🚀 Testing SME ERP RBAC System")
    
    # Test basic connectivity
    test_endpoint("GET", f"{BASE_URL}/", description="Test server connectivity")
    
    # Run RBAC tests
    test_rbac_policies()
    
    print("\n" + "="*60)
    print("🎯 RBAC Test Summary")
    print("="*60)
    print("✅ If all tests show expected results, RBAC is working correctly!")
    print("- VIEWER: Read-only access to items and stock")
    print("- STAFF: Read + create items and transactions")  
    print("- ADMIN: Full access including locations and deletions")

if __name__ == "__main__":
    main()