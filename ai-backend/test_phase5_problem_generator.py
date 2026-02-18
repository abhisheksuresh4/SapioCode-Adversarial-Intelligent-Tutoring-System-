"""Test Problem Generator - Phase 5"""
import asyncio
import json


async def test_problem_generator():
    """Test the new Problem Generator endpoints"""
    import requests
    
    base_url = "http://localhost:8000/api/ai"
    
    print("\n" + "="*60)
    print("TESTING PROBLEM GENERATOR (TEACHER TOOL)")
    print("="*60)
    
    # Test 1: Generate a problem from description
    print("\n1️⃣ TEST: Generate Problem from Natural Language")
    print("-" * 60)
    
    problem_request = {
        "raw_description": """
        Create a function that takes a list of integers and returns 
        the longest increasing subsequence. For example, given [10, 9, 2, 5, 3, 7, 101, 18],
        the longest increasing subsequence is [2, 3, 7, 101] with length 4.
        """,
        "language": "python",
        "difficulty": "medium",
        "num_test_cases": 5
    }
    
    print(f"📝 Input Description: {problem_request['raw_description'][:80]}...")
    print(f"🎯 Language: {problem_request['language']}, Difficulty: {problem_request['difficulty']}")
    
    try:
        response = requests.post(
            f"{base_url}/generate-problem",
            json=problem_request,
            timeout=60  # Longer timeout for AI generation
        )
        
        if response.status_code == 200:
            result = response.json()
            problem = result["problem"]
            
            print("\n✅ Problem Generated Successfully!")
            print(f"\n📌 Title: {problem['title']}")
            print(f"\n📖 Description:\n{problem['description'][:200]}...")
            print(f"\n🎓 Concepts: {', '.join(problem['concepts'])}")
            print(f"\n💻 Starter Code:\n{problem['starter_code']}")
            print(f"\n🧪 Test Cases Generated: {len(problem['test_cases'])}")
            
            # Show first test case
            if problem['test_cases']:
                tc = problem['test_cases'][0]
                print(f"\n   Example Test Case:")
                print(f"   Input: {tc['input']}")
                print(f"   Expected: {tc['expected_output']}")
                print(f"   Explanation: {tc['explanation']}")
            
            print(f"\n💡 Hints Provided: {len(problem['hints'])}")
            for i, hint in enumerate(problem['hints'], 1):
                print(f"   Hint {i}: {hint[:60]}...")
            
            # Test 2: Generate additional test cases
            print("\n\n2️⃣ TEST: Generate Additional Test Cases")
            print("-" * 60)
            
            additional_request = {
                "problem_description": problem['description'],
                "existing_test_cases": problem['test_cases'],
                "num_additional": 3
            }
            
            response2 = requests.post(
                f"{base_url}/generate-test-cases",
                json=additional_request,
                timeout=60
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"\n✅ Generated {len(result2['new_test_cases'])} Additional Test Cases!")
                
                for i, tc in enumerate(result2['new_test_cases'], 1):
                    print(f"\n   Test Case {i}:")
                    print(f"   Input: {tc['input']}")
                    print(f"   Expected: {tc['expected_output']}")
                    print(f"   Explanation: {tc['explanation']}")
                    print(f"   Hidden: {tc['is_hidden']}")
            else:
                print(f"❌ Additional Test Cases Failed: {response2.status_code}")
                print(response2.text)
        
        else:
            print(f"❌ Problem Generation Failed: {response.status_code}")
            print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server")
        print("💡 Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test 3: Quick problem generation
    print("\n\n3️⃣ TEST: Quick Easy Problem")
    print("-" * 60)
    
    easy_request = {
        "raw_description": "Write a function to check if a number is prime",
        "language": "python",
        "difficulty": "easy",
        "num_test_cases": 3
    }
    
    try:
        response = requests.post(
            f"{base_url}/generate-problem",
            json=easy_request,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            problem = result["problem"]
            
            print(f"✅ Quick Problem Generated!")
            print(f"📌 Title: {problem['title']}")
            print(f"💻 Starter Code:\n{problem['starter_code']}")
            print(f"🧪 Test Cases: {len(problem['test_cases'])}")
        else:
            print(f"❌ Failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "="*60)
    print("✨ PROBLEM GENERATOR TESTING COMPLETE")
    print("="*60)
    print("\n📚 Use Case: Teachers can now generate curriculum content by")
    print("   describing problems in natural language - the AI creates:")
    print("   ✓ Formal problem statements")
    print("   ✓ Starter code templates")
    print("   ✓ Comprehensive test cases")
    print("   ✓ Socratic-style hints")
    print("   ✓ Edge case coverage")
    print("\n")


if __name__ == "__main__":
    print("\n🚀 Starting Problem Generator Tests...")
    print("📡 Make sure server is running on http://localhost:8000")
    
    asyncio.run(test_problem_generator())
