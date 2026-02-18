"""Problem Generator - Teacher tool to create curriculum content"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel
from app.services.groq_service import get_groq_service


@dataclass
class ProblemTestCase:
    """A single test case for a problem"""
    input: str
    expected_output: str
    explanation: str
    is_hidden: bool = False  # Hidden test cases for evaluation


# Backward-compatible alias
TestCase = ProblemTestCase


@dataclass
class ProblemSpecification:
    """Complete problem specification with test cases"""
    title: str
    description: str
    difficulty: str  # easy, medium, hard
    concepts: List[str]  # ["loops", "arrays", "recursion"]
    starter_code: str
    solution_template: str
    test_cases: List[TestCase]
    hints: List[str]
    time_limit_seconds: int = 30
    memory_limit_mb: int = 128


class ProblemGenerator:
    """
    Generates structured programming problems from natural language descriptions.
    This is the "Teacher Tool" for the AI Engineer role.
    """
    
    def __init__(self):
        self.groq_service = get_groq_service()
        self.supported_languages = ["python", "javascript", "java", "cpp"]
    
    async def generate_problem_from_text(
        self,
        raw_description: str,
        language: str = "python",
        difficulty: str = "medium",
        num_test_cases: int = 5
    ) -> ProblemSpecification:
        """
        Convert raw problem description into structured problem with test cases.
        
        Args:
            raw_description: Natural language problem description
            language: Target programming language
            difficulty: Problem difficulty level
            num_test_cases: Number of test cases to generate
            
        Returns:
            ProblemSpecification with all components
        """
        if language not in self.supported_languages:
            raise ValueError(f"Language {language} not supported")
        
        # Generate structured problem specification
        spec_prompt = self._build_specification_prompt(
            raw_description, language, difficulty, num_test_cases
        )
        
        spec_response = await self.groq_service.generate_structured_response(
            spec_prompt,
            system_prompt="You are an expert computer science educator creating programming problems."
        )
        
        # Parse the response into structured format
        problem_spec = self._parse_problem_specification(spec_response, language)
        
        return problem_spec
    
    def _build_specification_prompt(
        self,
        description: str,
        language: str,
        difficulty: str,
        num_test_cases: int
    ) -> str:
        """Build prompt for generating problem specification"""
        return f"""Convert this problem description into a structured programming problem:

PROBLEM DESCRIPTION:
{description}

TARGET LANGUAGE: {language}
DIFFICULTY: {difficulty}

Generate the following components:

1. **Title**: Clear, concise problem title
2. **Description**: Formal problem statement with:
   - What the function should do
   - Input format and constraints
   - Output format
   - Examples

3. **Concepts**: List of programming concepts required (e.g., arrays, loops, recursion)

4. **Starter Code**: Basic function signature with comments in {language}

5. **Test Cases**: {num_test_cases} test cases with:
   - Input (as string representation)
   - Expected output (as string representation)
   - Brief explanation of what the test checks
   - Mark 2 of them as "hidden" (for evaluation only)

6. **Hints**: 3 progressive hints (Socratic style):
   - Hint 1: Guiding question (doesn't reveal approach)
   - Hint 2: Conceptual nudge (points to relevant concept)
   - Hint 3: Algorithmic direction (suggests approach without code)

7. **Solution Template**: Pseudocode or step-by-step approach outline

Format your response as JSON with these exact keys:
{{
  "title": "...",
  "description": "...",
  "difficulty": "{difficulty}",
  "concepts": ["...", "..."],
  "starter_code": "...",
  "solution_template": "...",
  "test_cases": [
    {{
      "input": "...",
      "expected_output": "...",
      "explanation": "...",
      "is_hidden": false
    }}
  ],
  "hints": ["...", "...", "..."]
}}"""
    
    def _parse_problem_specification(
        self,
        response: str,
        language: str
    ) -> ProblemSpecification:
        """Parse AI response into ProblemSpecification object"""
        import json
        
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            data = json.loads(json_str)
            
            # Convert test cases
            test_cases = [
                TestCase(
                    input=tc["input"],
                    expected_output=tc["expected_output"],
                    explanation=tc["explanation"],
                    is_hidden=tc.get("is_hidden", False)
                )
                for tc in data["test_cases"]
            ]
            
            return ProblemSpecification(
                title=data["title"],
                description=data["description"],
                difficulty=data["difficulty"],
                concepts=data["concepts"],
                starter_code=data["starter_code"],
                solution_template=data["solution_template"],
                test_cases=test_cases,
                hints=data["hints"]
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Failed to parse problem specification: {str(e)}")
    
    async def generate_additional_test_cases(
        self,
        problem_description: str,
        existing_test_cases: List[TestCase],
        num_additional: int = 3
    ) -> List[TestCase]:
        """
        Generate additional test cases for an existing problem.
        Useful for expanding test coverage.
        """
        existing_cases_str = "\n".join([
            f"Input: {tc.input} -> Output: {tc.expected_output}"
            for tc in existing_test_cases
        ])
        
        prompt = f"""Given this problem and existing test cases, generate {num_additional} NEW test cases that cover different edge cases:

PROBLEM:
{problem_description}

EXISTING TEST CASES:
{existing_cases_str}

Generate test cases that cover:
- Edge cases (empty input, single element, maximum size)
- Corner cases (negative numbers, special characters)
- Different algorithmic paths

Format as JSON array:
[
  {{
    "input": "...",
    "expected_output": "...",
    "explanation": "...",
    "is_hidden": true
  }}
]"""
        
        response = await self.groq_service.generate_structured_response(
            prompt,
            system_prompt="You are an expert at creating comprehensive test cases."
        )
        
        # Parse response
        import json
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        json_str = response[json_start:json_end]
        
        test_data = json.loads(json_str)
        
        return [
            TestCase(
                input=tc["input"],
                expected_output=tc["expected_output"],
                explanation=tc["explanation"],
                is_hidden=tc.get("is_hidden", True)
            )
            for tc in test_data
        ]
    
    async def refine_problem_difficulty(
        self,
        problem_spec: ProblemSpecification,
        target_difficulty: str
    ) -> ProblemSpecification:
        """
        Adjust problem difficulty by modifying constraints or requirements.
        
        Args:
            problem_spec: Current problem specification
            target_difficulty: Desired difficulty (easier/harder)
        """
        prompt = f"""Adjust this problem to be {target_difficulty}:

CURRENT PROBLEM:
Title: {problem_spec.title}
Description: {problem_spec.description}
Current Difficulty: {problem_spec.difficulty}

TARGET DIFFICULTY: {target_difficulty}

Suggest modifications to:
1. Input constraints (size, range, complexity)
2. Output requirements (additional requirements or simplifications)
3. Time/space complexity expectations

Return the modified description and updated difficulty level as JSON:
{{
  "description": "...",
  "difficulty": "...",
  "suggested_changes": "..."
}}"""
        
        response = await self.groq_service.generate_structured_response(
            prompt,
            system_prompt="You are an expert at calibrating problem difficulty."
        )
        
        # Update problem spec with new difficulty
        import json
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        data = json.loads(response[json_start:json_end])
        
        problem_spec.description = data["description"]
        problem_spec.difficulty = data["difficulty"]
        
        return problem_spec


# Singleton instance
_problem_generator_instance: Optional[ProblemGenerator] = None


def get_problem_generator() -> ProblemGenerator:
    """Get singleton ProblemGenerator instance"""
    global _problem_generator_instance
    if _problem_generator_instance is None:
        _problem_generator_instance = ProblemGenerator()
    return _problem_generator_instance
