"""
Phase 3 Test Script - Viva Voce System

Tests the complete Viva flow:
1. Start a Viva session
2. Get questions
3. Submit answers (simulated transcription)
4. Get verdict
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000/api"

# Sample code for testing
TEST_CODE = '''
def factorial(n):
    """Calculate factorial of n"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def find_max(numbers):
    """Find the maximum number in a list"""
    if not numbers:
        return None
    max_num = numbers[0]
    for num in numbers:
        if num > max_num:
            max_num = num
    return max_num

result = factorial(5)
print(f"5! = {result}")
'''


async def test_viva_flow():
    """Test the complete Viva Voce flow"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("PHASE 3 TEST: Viva Voce System")
        print("=" * 60)
        
        # Test 1: Start Viva Session
        print("\n📝 Test 1: Starting Viva Session...")
        response = await client.post(
            f"{BASE_URL}/viva/start",
            json={
                "student_id": "test_student_001",
                "code": TEST_CODE,
                "num_questions": 3
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data["session_id"]
            print(f"   ✅ Session started: {session_id[:8]}...")
            print(f"   📊 Questions generated: {data['total_questions']}")
            print(f"   ❓ First question: {data['first_question']}")
            print(f"   🔍 Code analysis:")
            print(f"      - Functions: {data['code_analysis']['functions_found']}")
            print(f"      - Loops: {data['code_analysis']['loops_found']}")
            print(f"      - Has recursion: {data['code_analysis']['has_recursion']}")
        else:
            print(f"   ❌ Failed: {response.text}")
            return
        
        # Test 2: Get Current Question
        print("\n📝 Test 2: Getting Current Question...")
        response = await client.get(f"{BASE_URL}/viva/question/{session_id}")
        
        if response.status_code == 200:
            q_data = response.json()
            print(f"   ✅ Question {q_data['question_number']}/{q_data['total_questions']}")
            print(f"   📌 Type: {q_data['question_type']}")
            print(f"   ❓ Question: {q_data['question_text']}")
            if q_data['target_code']:
                print(f"   💻 Target code: {q_data['target_code'][:50]}...")
        else:
            print(f"   ❌ Failed: {response.text}")
            return
        
        # Test 3: Submit Answer (simulating transcription)
        print("\n📝 Test 3: Submitting Answer...")
        
        # Simulate student answers
        simulated_answers = [
            "The factorial function calculates the factorial of a number n. It uses recursion, calling itself with n-1 until it reaches the base case of n equals 1 or less, where it returns 1. The final result is the product of all numbers from 1 to n.",
            "This line iterates through each number in the list. It's a for loop that checks each element one by one to compare with the current maximum value.",
            "If the input is empty or None, the function returns None. This handles the edge case where there are no numbers to find a maximum from."
        ]
        
        for i, answer in enumerate(simulated_answers):
            print(f"\n   📣 Answer {i+1}: '{answer[:50]}...'")
            
            response = await client.post(
                f"{BASE_URL}/viva/answer",
                json={
                    "session_id": session_id,
                    "transcribed_text": answer,
                    "audio_duration_seconds": 15.0
                }
            )
            
            if response.status_code == 200:
                eval_data = response.json()
                score_emoji = "🟢" if eval_data['score'] >= 0.7 else "🟡" if eval_data['score'] >= 0.4 else "🔴"
                print(f"   {score_emoji} Score: {eval_data['score']:.2f}")
                print(f"   ✓ Matched: {eval_data['matched_concepts']}")
                print(f"   ✗ Missing: {eval_data['missing_concepts']}")
                print(f"   💬 Feedback: {eval_data['feedback'][:80]}...")
                
                if not eval_data['has_more_questions']:
                    print("   📝 No more questions!")
                    break
            else:
                print(f"   ❌ Failed: {response.text}")
                # Continue to next question anyway
        
        # Test 4: Get Verdict
        print("\n📝 Test 4: Getting Final Verdict...")
        response = await client.get(f"{BASE_URL}/viva/verdict/{session_id}")
        
        if response.status_code == 200:
            verdict_data = response.json()
            verdict_emoji = {
                "pass": "🏆",
                "weak": "⚠️",
                "fail": "❌"
            }.get(verdict_data['verdict'], "❓")
            
            print(f"   {verdict_emoji} VERDICT: {verdict_data['verdict'].upper()}")
            print(f"   📊 Average Score: {verdict_data['average_score']:.2f}")
            print(f"   💬 Message: {verdict_data['message']}")
            print(f"\n   📋 Question Breakdown:")
            for q in verdict_data['question_breakdown']:
                print(f"      - {q['question'][:40]}... → {q['score']:.2f}")
            print(f"\n   🎯 Improvement Areas: {verdict_data['improvement_areas']}")
        else:
            print(f"   ❌ Failed: {response.text}")
        
        # Test 5: Health Check
        print("\n📝 Test 5: Viva Health Check...")
        response = await client.get(f"{BASE_URL}/viva/health")
        
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Status: {health['status']}")
            print(f"   📊 Active sessions: {health['active_sessions']}")
            print(f"   🎤 Whisper available: {health['whisper_available']}")
        
        # Cleanup
        print("\n📝 Cleanup: Ending session...")
        await client.delete(f"{BASE_URL}/viva/session/{session_id}")
        print("   ✅ Session ended")
        
        print("\n" + "=" * 60)
        print("PHASE 3 TESTS COMPLETE!")
        print("=" * 60)


def run_tests():
    """Run all Phase 3 tests"""
    print("\n⚠️  Make sure the server is running!")
    print("   Start it with: uvicorn app.main:app --reload")
    print("-" * 60)
    
    asyncio.run(test_viva_flow())


if __name__ == "__main__":
    run_tests()
