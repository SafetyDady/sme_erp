#!/usr/bin/env python3
"""RBAC Matrix Testing for Production Sign-off"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Create test tokens manually (bypass database for now)
from app.core.auth.jwt import create_access_token

# Test tokens for RBAC validation
def create_test_tokens():
    tokens = {
        'viewer': create_access_token(subject="1"),    # VIEWER user_id=1  
        'staff': create_access_token(subject="2"),     # STAFF user_id=2
        'admin': create_access_token(subject="3"),     # ADMIN user_id=3
    }
    return tokens

def test_rbac_matrix():
    print("🎯 Phase 2B: RBAC Matrix Validation")
    print("="*50)
    
    # Create tokens
    tokens = create_test_tokens()
    
    # Test cases for Production sign-off
    test_cases = [
        {
            "name": "VIEWER → POST /inventory/items (should 403)",
            "method": "POST",
            "url": f"{BASE_URL}/api/v1/inventory/items",
            "token": tokens['viewer'],
            "data": {"name": "Test Item", "quantity": 5, "price": 100},
            "expected": 403
        },
        {
            "name": "STAFF → DELETE /inventory/items/1 (should 403)",  
            "method": "DELETE",
            "url": f"{BASE_URL}/api/v1/inventory/items/1",
            "token": tokens['staff'],
            "expected": 403
        },
        {
            "name": "ADMIN → PUT /inventory/items/1 (should 200)",
            "method": "PUT", 
            "url": f"{BASE_URL}/api/v1/inventory/items/1",
            "token": tokens['admin'],
            "data": {"name": "Updated Item", "quantity": 10, "price": 200},
            "expected": 200
        },
        {
            "name": "ADMIN → POST /inventory/locations (should 200)",
            "method": "POST",
            "url": f"{BASE_URL}/api/v1/inventory/locations", 
            "token": tokens['admin'],
            "data": {"name": "Admin Location", "address": "Test Address"},
            "expected": 200
        }
    ]
    
    results = []
    for test in test_cases:
        result = run_test(test)
        results.append(result)
    
    # Summary
    passed = len([r for r in results if r['passed']])
    total = len(results)
    
    print(f"\n🏆 RBAC Matrix Results: {passed}/{total}")
    if passed == total:
        print("✅ Production RBAC READY: APPROVED")
    else:
        print("❌ Production RBAC READY: FAILED")
        print("   Fix failing tests before production deployment")

def run_test(test_case):
    print(f"\n🧪 {test_case['name']}")
    
    headers = {"Authorization": f"Bearer {test_case['token']}"}
    
    try:
        if test_case['method'] == 'GET':
            response = requests.get(test_case['url'], headers=headers)
        elif test_case['method'] == 'POST':
            response = requests.post(test_case['url'], json=test_case.get('data'), headers=headers)
        elif test_case['method'] == 'PUT':
            response = requests.put(test_case['url'], json=test_case.get('data'), headers=headers)
        elif test_case['method'] == 'DELETE':
            response = requests.delete(test_case['url'], headers=headers)
        
        actual_status = response.status_code
        expected_status = test_case['expected']
        passed = actual_status == expected_status
        
        print(f"   Expected: {expected_status} | Actual: {actual_status}")
        print(f"   Result: {'✅ PASS' if passed else '❌ FAIL'}")
        
        if not passed:
            print(f"   Response: {response.text[:100]}")
            
        return {
            'name': test_case['name'],
            'passed': passed,
            'expected': expected_status,
            'actual': actual_status
        }
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return {
            'name': test_case['name'], 
            'passed': False,
            'error': str(e)
        }

if __name__ == "__main__":
    test_rbac_matrix()
