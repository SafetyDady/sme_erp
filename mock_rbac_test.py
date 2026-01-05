#!/usr/bin/env python3
"""Simple RBAC Test with Mocked Users"""
import requests
from app.core.auth.jwt import create_access_token

BASE_URL = "http://localhost:8000"

def test_rbac_matrix():
    print("🎯 Phase 2B: RBAC Matrix Validation")
    print("=" * 50)
    
    # Create mock tokens (user_id based)
    tokens = {
        'viewer': create_access_token(subject="999"),    # Mock VIEWER
        'staff': create_access_token(subject="998"),     # Mock STAFF  
        'admin': create_access_token(subject="997"),     # Mock ADMIN
    }
    
    print(f"📋 Test Tokens Created:")
    for role, token in tokens.items():
        print(f"   {role.upper()}: {token[:30]}...")
    
    print(f"\n🧪 Testing RBAC Matrix...")
    
    # Test 1: VIEWER → POST (should 403)
    print(f"\n1️⃣ VIEWER → POST /inventory/items")
    response = requests.post(
        f"{BASE_URL}/api/v1/inventory/items",
        json={"name": "Test", "quantity": 5, "price": 100},
        headers={"Authorization": f"Bearer {tokens['viewer']}"}
    )
    print(f"   Expected: 403 | Actual: {response.status_code} | {'✅ PASS' if response.status_code == 403 else '❌ FAIL'}")
    
    # Test 2: STAFF → DELETE (should 403)  
    print(f"\n2️⃣ STAFF → DELETE /inventory/items/1")
    response = requests.delete(
        f"{BASE_URL}/api/v1/inventory/items/1",
        headers={"Authorization": f"Bearer {tokens['staff']}"}
    )
    print(f"   Expected: 403 | Actual: {response.status_code} | {'✅ PASS' if response.status_code == 403 else '❌ FAIL'}")
    
    # Test 3: ADMIN → PUT (should 200)
    print(f"\n3️⃣ ADMIN → PUT /inventory/items/1")
    response = requests.put(
        f"{BASE_URL}/api/v1/inventory/items/1", 
        json={"name": "Updated", "quantity": 10, "price": 200},
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    print(f"   Expected: 200 | Actual: {response.status_code} | {'✅ PASS' if response.status_code == 200 else '❌ FAIL'}")
    
    # Test 4: ADMIN → POST locations (should 200)
    print(f"\n4️⃣ ADMIN → POST /inventory/locations")
    response = requests.post(
        f"{BASE_URL}/api/v1/inventory/locations",
        json={"name": "Test Location", "address": "Test Address"},
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    print(f"   Expected: 200 | Actual: {response.status_code} | {'✅ PASS' if response.status_code == 200 else '❌ FAIL'}")

if __name__ == "__main__":
    test_rbac_matrix()
