"""Simple API endpoint test using requests"""
import requests
import json


def test_problem_generator_endpoints():
    """Test the Problem Generator API endpoints"""
    base_url = "http://localhost:8000/api/ai"
    
    print("\n" + "="*70)
    print("🧪 PROBLEM GENERATOR API ENDPOINT TESTS")
    print("="*70)
    
    # Test 1: Generate Problem
    print("\n📝 Test 1: POST /api/ai/generate-problem")
    print("-" * 70)
    
    request_data = {
        "raw_description": "Write a function to reverse a string",
        "language": "python",
        "difficulty": "easy",
        "num_test_cases": 3
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/generate-problem",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            problem = result.get("problem", {})
            
            print(f"\n✅ Status: {response.status_code}")
            print(f"✅ Title: {problem.get('title')}")
            print(f"✅ Difficulty: {problem.get('difficulty')}")
            print(f"✅ Test Cases: {len(problem.get('test_cases', []))}")
            print(f"✅ Hints: {len(problem.get('hints', []))}")
            print(f"✅ Concepts: {', '.join(problem.get('concepts', [])[:3])}")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Server not running!")
        print("💡 Start server: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    # Test 2: Generate Additional Test Cases
    print("\n\n📝 Test 2: POST /api/ai/generate-test-cases")
    print("-" * 70)
    
    if response.status_code == 200:
        problem = result.get("problem", {})
        
        request_data = {
            "problem_description": problem.get("description", "Reverse a string"),
            "existing_test_cases": problem.get("test_cases", []),
            "num_additional": 2
        }
        
        try:
            response2 = requests.post(
                f"{base_url}/generate-test-cases",
                json=request_data,
                timeout=60
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                new_cases = result2.get("new_test_cases", [])
                
                print(f"✅ Status: {response2.status_code}")
                print(f"✅ New Test Cases Generated: {len(new_cases)}")
                
                for i, tc in enumerate(new_cases, 1):
                    print(f"\n   Case {i}:")
                    print(f"   - Input: {tc.get('input', '')[:50]}")
                    print(f"   - Output: {tc.get('expected_output', '')[:50]}")
                    print(f"   - Hidden: {tc.get('is_hidden', False)}")
            else:
                print(f"❌ Status: {response2.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "="*70)
    print("✨ API ENDPOINT TESTS COMPLETE")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Testing Problem Generator API Endpoints...")
    print("📡 Ensure server is running: uvicorn app.main:app --reload\n")
    
    test_problem_generator_endpoints()
