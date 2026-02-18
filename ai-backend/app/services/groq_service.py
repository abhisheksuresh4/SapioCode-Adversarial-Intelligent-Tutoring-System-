import httpx
from typing import Optional, List, Dict
from app.core.config import get_settings


class GroqService:
    """Service for interacting with Groq AI API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            base_url=self.settings.GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat completion request to Groq
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Randomness (0-2)
            max_tokens: Max response length
            response_format: Optional format (e.g., {"type": "json_object"})
        
        Returns:
            AI response text
        """
        try:
            # Groq API request payload
            payload = {
                "messages": messages,
                "model": self.settings.GROQ_MODEL,
                "stream": False,
                "temperature": temperature
            }
            
            # Add response format if specified (for JSON mode)
            if response_format:
                payload["response_format"] = response_format
            
            response = await self.client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            print(f"Groq API Error: {e.response.status_code}")
            print(f"Error details: {error_detail}")
            raise Exception(f"Groq API Error: {error_detail}")
        except Exception as e:
            print(f"Error calling Groq: {str(e)}")
            raise
    
    async def generate_hint(
        self,
        problem_description: str,
        student_code: str,
        stuck_duration: int
    ) -> str:
        """
        Generate a Socratic hint for stuck student
        
        Args:
            problem_description: The problem the student is trying to solve
            student_code: Current code written by student
            stuck_duration: How long they've been stuck (seconds)
        
        Returns:
            A Socratic question to guide the student
        """
        
        prompt = f"""You are a programming tutor using the Socratic method.

PROBLEM:
{problem_description}

STUDENT'S CODE:
```
{student_code}
```

The student has been stuck for {stuck_duration} seconds.

Generate a SOCRATIC QUESTION (not a direct answer) that guides them toward the solution.
The question should make them think about their approach without revealing the answer."""

        messages = [
            {"role": "system", "content": "You are a patient CS tutor who never gives direct answers. You guide students through questions."},
            {"role": "user", "content": prompt}
        ]
        
        return await self.chat_completion(messages, temperature=0.8)
    
    async def generate_structured_response(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a structured (JSON) response from the LLM.

        Convenience wrapper around chat_completion that sets up
        system/user messages and requests JSON output format.

        Args:
            prompt: The user prompt describing what to generate
            system_prompt: System-level instruction for the model
            temperature: Randomness (0-2)
            max_tokens: Max response length

        Returns:
            Raw AI response text (expected to contain JSON)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        return await self.chat_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
_groq_service: Optional[GroqService] = None


def get_groq_service() -> GroqService:
    """Get or create the Groq service singleton"""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service
