"""
Mock Frontend Test Script
-------------------------
This script simulates what Role 1 (Frontend) will send to your API.
Use this to verify your endpoints work BEFORE integration.

Run this with the server running:
1. Terminal 1: venv\\Scripts\\python -m uvicorn app.main:app --reload
2. Terminal 2: venv\\Scripts\\python mock_frontend_test.py
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

def print_response(endpoint: str, response: requests.Response):
    """Pretty print API response"""
    print(f"\n{'='*70}")
    print(f"Endpoint: {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
    print(f"{'='*70}\n")

def test_basic_hint():
    """Test 1: Basic Hint Generation (Core Feature)"""
    print("\n🧪 TEST 1: Basic Hint Generation")
    
    url = f"{BASE_URL}{API_PREFIX}/ai/hint"
    payload = {
        "problem_description": "Write a function to calculate factorial",
        "student_code": "def factorial(n):\n    return n",
        # Note: NOT sending stuck_duration - testing default
    }
    
    try:
        response = requests.post(url, json=payload)
        print_response("/ai/hint", response)
        
        if response.status_code == 200:
            data = response.json()
            assert "hint" in data, "Response missing 'hint' field"
            print("✅ PASS: Basic hint generation works")
            return True
        else:
            print("❌ FAIL: Non-200 status code")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

def test_code_analysis():
    """Test 2: Code Analysis (Core Feature)"""
    print("\n🧪 TEST 2: Code Analysis")
    
    url = f"{BASE_URL}{API_PREFIX}/ai/analyze"
    payload = {
        "code": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)",
        "language": "python"
    }
    
    try:
        response = requests.post(url, json=payload)
        print_response("/ai/analyze", response)
        
        if response.status_code == 200:
            data = response.json()
            assert "metrics" in data, "Response missing 'metrics' field"
            print("✅ PASS: Code analysis works")
            return True
        else:
            print("❌ FAIL: Non-200 status code")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

def test_smart_hint():
    """Test 3: Smart Hint with Context (Advanced Feature)"""
    print("\n🧪 TEST 3: Smart Hint with Full Context")
    
    url = f"{BASE_URL}{API_PREFIX}/ai/hint/smart"
    payload = {
        "problem_description": "Write a function to find even numbers in a list",
        "student_code": "def find_evens(nums):\n    result = []\n    # stuck here",
        "time_stuck": 120,  # 2 minutes
        "frustration_level": 0.6,
        "previous_hints_count": 1,
        "code_attempts": 3
    }
    
    try:
        response = requests.post(url, json=payload)
        print_response("/ai/hint/smart", response)
        
        if response.status_code == 200:
            data = response.json()
            assert "hint" in data, "Response missing 'hint' field"
            assert "hint_level" in data, "Response missing 'hint_level' field"
            print("✅ PASS: Smart hint generation works")
            return True
        else:
            print("❌ FAIL: Non-200 status code")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

def test_viva_start():
    """Test 4: Viva Voce Session (Phase 3 Feature)"""
    print("\n🧪 TEST 4: Viva Voce Session Start")
    
    url = f"{BASE_URL}{API_PREFIX}/viva/start"
    payload = {
        "student_id": "test_student_001",
        "problem_id": "recursion_basics",
        "code": "def factorial(n):\n    if n == 0: return 1\n    return n * factorial(n-1)"
    }
    
    try:
        response = requests.post(url, json=payload)
        print_response("/viva/start", response)
        
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data, "Response missing 'session_id' field"
            print("✅ PASS: Viva session creation works")
            return True
        else:
            print("❌ FAIL: Non-200 status code")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

def test_health_check():
    """Test 5: Health Check"""
    print("\n🧪 TEST 5: Health Check")
    
    url = f"{BASE_URL}{API_PREFIX}/ai/status"
    
    try:
        response = requests.get(url)
        print_response("/ai/status", response)
        
        if response.status_code == 200:
            print("✅ PASS: Health check works")
            return True
        else:
            print("❌ FAIL: Non-200 status code")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("🚀 MOCK FRONTEND INTEGRATION TESTS")
    print("="*70)
    print("\nMake sure the server is running:")
    print("  venv\\Scripts\\python -m uvicorn app.main:app --reload")
    print("\n" + "="*70)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Basic Hint", test_basic_hint()))
    results.append(("Code Analysis", test_code_analysis()))
    results.append(("Smart Hint", test_smart_hint()))
    results.append(("Viva Session", test_viva_start()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your API is ready for integration.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Fix these before integration.")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    run_all_tests()
