"""Quick test to verify Groq API key is loaded correctly"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get the API key
api_key = os.getenv("GROQ_API_KEY")

print("=" * 50)
print("Groq API Key Test")
print("=" * 50)
print(f"API Key exists: {api_key is not None}")
print(f"API Key starts with 'gsk_': {api_key.startswith('gsk_') if api_key else False}")
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"First 10 chars: {api_key[:10] if api_key else 'None'}...")
print(f"Last 4 chars: ...{api_key[-4:] if api_key else 'None'}")
print("=" * 50)

# Now test the actual Groq API call
import httpx
import asyncio

async def test_groq():
    client = httpx.AsyncClient(
        base_url="https://api.groq.com/openai/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=30.0
    )
    
    try:
        print("\nTesting Groq API...")
        response = await client.post(
            "/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Say 'Hello' in one word"}],
                "model": "llama-3.3-70b-versatile",
                "stream": False,
                "temperature": 0.7
            }
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Response: {data['choices'][0]['message']['content']}")
        else:
            print("❌ FAILED!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        await client.aclose()

# Run the test
asyncio.run(test_groq())
