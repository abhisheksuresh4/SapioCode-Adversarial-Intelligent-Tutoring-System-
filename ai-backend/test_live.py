"""
Live API test script — run this WHILE the server is running on port 8002.
Usage: python test_live.py
"""
import requests
import json
import sys

BASE = "http://localhost:8002"

def test(name, method, path, body=None, expect_status=200):
    url = f"{BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=60)
        else:
            r = requests.post(url, json=body, timeout=60)
        
        status = "PASS" if r.status_code == expect_status else "FAIL"
        print(f"\n[{status}] [{r.status_code}] {name}")
        print(f"   {method} {path}")
        
        try:
            data = r.json()
            pretty = json.dumps(data, indent=2)
            if len(pretty) > 600:
                print(f"   Response: {pretty[:600]}...")
            else:
                print(f"   Response: {pretty}")
        except:
            print(f"   Response: {r.text[:300]}")
        
        return r.status_code == expect_status
    except requests.ConnectionError:
        print(f"\n[FAIL] {name} -- CONNECTION REFUSED. Is the server running on port 8002?")
        return False
    except Exception as e:
        print(f"\n[FAIL] {name} -- ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("  SapioCode AI Backend -- Live API Tests")
    print("=" * 60)
    
    results = []

    # --- 1: Health ---
    results.append(test(
        "1. Health Check",
        "GET", "/health"
    ))

    # --- 2: AST Analysis (FR-2) ---
    results.append(test(
        "2. AST Analysis (FR-2) -- Recursive Fibonacci",
        "POST", "/api/ai/analyze",
        body={
            "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            "language": "python"
        }
    ))

    # --- 3: Socratic Hint (FR-3) via /api/ai/hint ---
    results.append(test(
        "3. Socratic Hint (FR-3) -- Basic Socratic guidance",
        "POST", "/api/ai/hint",
        body={
            "problem_description": "Write a function two_sum(nums, target) that returns indices of two numbers that add up to target.",
            "student_code": "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i,j]",
            "stuck_duration": 120
        }
    ))

    # --- 4: Smart Hint with frustration (FR-3 + FR-6) ---
    results.append(test(
        "4. Smart Hint (FR-6) -- High frustration intervention",
        "POST", "/api/ai/hint/smart",
        body={
            "problem_description": "Write a function two_sum(nums, target) that returns indices of two numbers that add up to target.",
            "student_code": "def two_sum(nums, target):\n    pass",
            "time_stuck": 300,
            "frustration_level": 0.9,
            "previous_hints_count": 3,
            "code_attempts": 5
        }
    ))

    # --- 5: Viva Start Session (FR-8) ---
    results.append(test(
        "5. Viva Start Session (FR-8) -- Questions from AST",
        "POST", "/api/viva/start",
        body={
            "student_id": "test_student_1",
            "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            "num_questions": 3
        }
    ))

    # --- 6: Viva Get Question ---
    results.append(test(
        "6. Viva Get Current Question",
        "GET", "/api/viva/question/test_student_1"
    ))

    # --- 7: Viva Submit Answer (FR-9) ---
    results.append(test(
        "7. Semantic Verification (FR-9) -- Submit answer",
        "POST", "/api/viva/answer",
        body={
            "session_id": "test_student_1",
            "transcribed_text": "I use recursion with a base case where n is 0 or 1, returning n directly. For larger values I add fibonacci of n minus 1 and n minus 2.",
            "audio_duration_seconds": 15.0
        }
    ))

    # --- 8: Viva Verdict ---
    results.append(test(
        "8. Viva Verdict -- Pass/Fail with confidence",
        "GET", "/api/viva/verdict/test_student_1"
    ))

    # --- 9: Full Pipeline (Integration Bridge) ---
    results.append(test(
        "9. Full Submit Pipeline (Integration Bridge)",
        "POST", "/api/integration/submit",
        body={
            "student_id": "test_student_1",
            "submission_id": "sub_live_001",
            "problem_description": "Write sum_digits(n) that returns sum of all digits of a non-negative integer.",
            "code": "def sum_digits(n):\n    total = 0\n    while n > 0:\n        total += n % 10\n        n = n // 10\n    return total",
            "language": "python",
            "concepts": ["loops", "variables"],
            "time_stuck": 60,
            "previous_hints": 1,
            "code_attempts": 2,
            "frustration": 0.3,
            "engagement": 0.8
        }
    ))

    # --- 10: LangGraph Hint (State Machine) ---
    results.append(test(
        "10. LangGraph State Machine -- Tutoring graph",
        "POST", "/api/integration/hint-graph",
        body={
            "problem_description": "Write two_sum function that returns indices of two numbers adding to target.",
            "code": "def two_sum(nums, t):\n    pass",
            "student_id": "test_student_1",
            "frustration": 0.5,
            "engagement": 0.6,
            "confusion": 0.3,
            "boredom": 0.1
        }
    ))

    # --- 11: Teacher Class Pulse ---
    results.append(test(
        "11. Teacher Class Pulse",
        "GET", "/api/teacher/class-pulse"
    ))

    # --- 12: Teacher At-Risk Students ---
    results.append(test(
        "12. Teacher At-Risk Students",
        "GET", "/api/teacher/at-risk"
    ))

    # --- 13: Teacher Student Profile ---
    results.append(test(
        "13. Teacher Student Profile",
        "GET", "/api/teacher/student/test_student_1"
    ))

    # --- 14: Teacher Mastery Heatmap ---
    results.append(test(
        "14. Teacher Mastery Heatmap",
        "GET", "/api/teacher/mastery-heatmap"
    ))

    # --- 15: Problem Generator (Teacher Tool) ---
    results.append(test(
        "15. Problem Generator -- Teacher creates problem",
        "POST", "/api/teacher/generate-problem",
        body={
            "raw_description": "Write a function that checks if a string is a palindrome",
            "difficulty": "easy",
            "concepts": ["strings", "loops"]
        }
    ))

    # --- Summary ---
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"  Results: {passed}/{total} passed")
    
    if passed == total:
        print("  ALL TESTS PASSED -- Your AI backend is fully working!")
    else:
        failed = total - passed
        print(f"  {failed} test(s) need attention (check responses above)")
    
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
