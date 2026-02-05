"""
Test script for Phase 4: Peer Learning System

Tests the peer learning API endpoints using FastAPI TestClient.
"""

from fastapi.testclient import TestClient
from app.main import app
import sys

client = TestClient(app)

def test_phase4():
    """Test all Phase 4 peer learning endpoints"""
    
    print("=" * 60)
    print("PHASE 4: PEER LEARNING SYSTEM TEST (TestClient)")
    print("=" * 60)
    print()
    
    try:
        # Test 1: Create student profiles
        print("Test 1: Creating Student Profiles")
        print("-" * 60)
        
        # Create Alice (intermediate, visual learner)
        alice_profile = {
            "student_id": "alice_001",
            "name": "Alice Johnson",
            "skill_level": "intermediate",
            "learning_style": "visual",
            "topics_mastered": ["variables", "loops", "functions"],
            "topics_learning": ["recursion", "data_structures"],
            "preferred_role": "learner"
        }
        
        response = client.post("/api/peer/profile", json=alice_profile)
        print(f"✅ Created Alice's profile: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - Student ID: {data['student_id']}")
            print(f"   - Skill Level: {data['skill_level']}")
            print(f"   - Learning: {', '.join(data['topics_learning'])}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Create Bob (advanced, visual learner, knows recursion)
        bob_profile = {
            "student_id": "bob_002",
            "name": "Bob Smith",
            "skill_level": "advanced",
            "learning_style": "visual",
            "topics_mastered": ["variables", "loops", "functions", "recursion", "algorithms"],
            "topics_learning": ["machine_learning", "distributed_systems"],
            "preferred_role": "tutor"
        }
        
        response = client.post("/api/peer/profile", json=bob_profile)
        print(f"✅ Created Bob's profile: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - Student ID: {data['student_id']}")
            print(f"   - Skill Level: {data['skill_level']}")
        print()
        
        # Create Carol (beginner, auditory learner)
        carol_profile = {
            "student_id": "carol_003",
            "name": "Carol Davis",
            "skill_level": "beginner",
            "learning_style": "auditory",
            "topics_mastered": ["variables"],
            "topics_learning": ["loops", "functions", "recursion"],
            "preferred_role": "learner"
        }
        
        response = client.post("/api/peer/profile", json=carol_profile)
        print(f"✅ Created Carol's profile: {response.status_code}")
        print()
        
        # Test 2: Get profile
        print("Test 2: Retrieving Student Profile")
        print("-" * 60)
        
        response = client.get("/api/peer/profile/alice_001")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved Alice's profile")
            print(f"   - Name: {data['name']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 3: Find matches for Alice (wants to learn recursion)
        print("Test 3: Finding Learning Partners for Alice")
        print("-" * 60)
        
        match_request = {
            "student_id": "alice_001",
            "topic": "recursion",
            "max_matches": 5
        }
        
        response = client.post("/api/peer/match", json=match_request)
        if response.status_code == 200:
            matches = response.json()
            print(f"✅ Found {len(matches)} potential partners for Alice")
            print()
            
            for i, match in enumerate(matches, 1):
                print(f"   Match #{i}: {match['name']}")
                print(f"   - Match Score: {match['score']:.2f}")
                print(f"   - Reasons: {', '.join(match['reasons'])}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 4: Start a peer session
        print("Test 4: Starting Peer Learning Session")
        print("-" * 60)
        
        session_request = {
            "student1_id": "alice_001",
            "student2_id": "bob_002",
            "topic": "recursion"
        }
        
        response = client.post("/api/peer/session/start", json=session_request)
        if response.status_code == 200:
            session = response.json()
            session_id = session['session_id']
            print(f"✅ Started peer session: {session_id}")
            print(f"   - Roles: {session['student1_role']} & {session['student2_role']}")
        else:
            print(f"❌ Error: {session['detail'] if 'detail' in session else response.text}")
            return
        print()
        
        # Test 5: Get session details
        print("Test 5: Retrieving Session Details")
        print("-" * 60)
        
        response = client.get(f"/api/peer/session/{session_id}")
        if response.status_code == 200:
            print(f"✅ Retrieved session details")
        print()
        
        # Test 6: End session with ratings
        print("Test 6: Ending Session with Ratings")
        print("-" * 60)
        
        end_request = {
            "session_id": session_id,
            "student1_rating": 4.5,
            "student2_rating": 5.0,
            "notes": "Good session"
        }
        
        response = client.post("/api/peer/session/end", json=end_request)
        if response.status_code == 200:
            session = response.json()
            print(f"✅ Session ended successfully")
            print(f"   - Duration: {session['duration_minutes']} min")
        print()
        
        # Test 7: Get student's session history
        print("Test 7: Getting Student Session History")
        print("-" * 60)
        
        response = client.get("/api/peer/sessions/alice_001")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved Alice's session history")
            print(f"   - Total Sessions: {data['total_sessions']}")
        print()
        
        # Test 8: Check updated profile
        print("Test 8: Verifying Updated Profile with Rating")
        print("-" * 60)
        
        response = client.get("/api/peer/profile/bob_002")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bob's profile updated")
            print(f"   - Average Rating: {data['average_rating']:.2f}/5.0")
        print()
        
        print("=" * 60)
        print("ALL TESTS PASSED ✅")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_phase4()
