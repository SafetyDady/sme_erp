#!/usr/bin/env python3
"""
Test script for OAuth2 Authentication API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def test_endpoint(method, url, data=None, headers=None, description=""):
    try:
        print(f"\n🧪 {description}")
        print(f"   {method} {url}")
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, data=data, headers=headers)
        
        print(f"   Status: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                result = response.json()
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

def main():
    print("🚀 Testing SME ERP OAuth2 Authentication System")
    
    # Test 1: Root endpoint (unprotected)
    test_endpoint("GET", f"{BASE_URL}/", description="Test 1: Root endpoint (unprotected)")
    
    # Test 2: Protected endpoint without token (should fail)
    test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/items", description="Test 2: Protected endpoint without token (should fail)")
    
    # Test 3: Login with correct credentials
    login_data = {
        "username": "admin@sme-erp.com",
        "password": "admin123"
    }
    token_response = test_endpoint("POST", f"{BASE_URL}/api/v1/auth/login", 
                                 data=login_data, 
                                 description="Test 3: Login with correct credentials")
    
    if token_response and isinstance(token_response, dict) and "access_token" in token_response:
        token = token_response["access_token"]
        print(f"   ✅ Got access token: {token[:30]}...")
        
        # Test 4: Protected endpoint with token (should work)
        headers = {"Authorization": f"Bearer {token}"}
        test_endpoint("GET", f"{BASE_URL}/api/v1/inventory/items", 
                     headers=headers, 
                     description="Test 4: Protected endpoint with token (should work)")
        
        # Test 5: User profile endpoint
        test_endpoint("GET", f"{BASE_URL}/api/v1/auth/me", 
                     headers=headers, 
                     description="Test 5: User profile endpoint")
        
        # Test 6: Create inventory item  
        create_data = {"name": "Test Item", "quantity": 5, "price": 100}
        test_endpoint("POST", f"{BASE_URL}/api/v1/inventory/items", 
                     data=json.dumps(create_data),
                     headers={**headers, "Content-Type": "application/json"}, 
                     description="Test 6: Create inventory item")
    else:
        print("   ❌ Failed to get access token")
    
    # Test 7: Login with wrong credentials (should fail)
    wrong_data = {
        "username": "wrong@email.com", 
        "password": "wrongpass"
    }
    test_endpoint("POST", f"{BASE_URL}/api/v1/auth/login", 
                 data=wrong_data, 
                 description="Test 7: Login with wrong credentials (should fail)")

if __name__ == "__main__":
    main()
