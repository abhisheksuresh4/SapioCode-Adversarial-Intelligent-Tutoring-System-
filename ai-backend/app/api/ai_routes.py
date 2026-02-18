from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.groq_service import get_groq_service
from app.services.code_analyzer import CodeAnalyzer
from app.services.tutoring_engine import (
    TutoringEngine,
    HintGenerator,
    StudentContext
)
from app.services.problem_generator import get_problem_generator


router = APIRouter()


# ===== REQUEST MODELS =====

class TestAIRequest(BaseModel):
    """Request model for testing AI"""
    message: str


class HintRequest(BaseModel):
    """Request model for generating hints (basic)"""
    problem_description: str
    student_code: str
    stuck_duration: int = 0


class AnalyzeCodeRequest(BaseModel):
    """Request for code analysis"""
    code: str
    language: str = "python"


class SmartHintRequest(BaseModel):
    """Request for intelligent hint with full context"""
    problem_description: str
    student_code: str
    time_stuck: int = Field(default=0, description="Seconds student has been stuck")
    frustration_level: float = Field(default=0.0, ge=0.0, le=1.0)
    previous_hints_count: int = Field(default=0, ge=0)
    code_attempts: int = Field(default=0, ge=0)


class InterventionCheckRequest(BaseModel):
    """Request to check if intervention is needed"""
    problem_description: str
    student_code: str
    time_stuck: int
    frustration_level: float = 0.0
    previous_hints: int = 0
    code_attempts: int = 0


class GenerateProblemRequest(BaseModel):
    """Request to generate a new problem from description"""
    raw_description: str = Field(..., description="Natural language problem description")
    language: str = Field(default="python", description="Target programming language")
    difficulty: str = Field(default="medium", description="Problem difficulty: easy, medium, hard")
    num_test_cases: int = Field(default=5, ge=3, le=10, description="Number of test cases")


class AdditionalTestCasesRequest(BaseModel):
    """Request to generate additional test cases"""
    problem_description: str
    existing_test_cases: list
    num_additional: int = Field(default=3, ge=1, le=5)


@router.post("/test")
async def test_ai(request: TestAIRequest):
    """
    Test endpoint to verify Groq API is working
    
    This is used to validate the connection and API key.
    """
    try:
        groq = get_groq_service()
        messages = [
            {"role": "user", "content": request.message}
        ]
        response = await groq.chat_completion(messages)
        return {
            "success": True,
            "response": response,
            "service": "groq"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API Error: {str(e)}")


@router.post("/hint")
async def generate_hint(request: HintRequest):
    """
    Generate a Socratic hint for stuck student
    
    This is the core tutoring functionality - it analyzes the student's
    code and generates a guiding question rather than giving the answer.
    """
    try:
        groq = get_groq_service()
        hint = await groq.generate_hint(
            request.problem_description,
            request.student_code,
            request.stuck_duration
        )
        return {
            "success": True,
            "hint": hint,
            "hint_type": "socratic",
            "stuck_duration": request.stuck_duration
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hint Generation Error: {str(e)}")


@router.get("/status")
async def ai_status():
    """Check if AI service is configured and ready"""
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        # Don't expose the actual key, just check if it exists
        has_key = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here")
        
        return {
            "configured": has_key,
            "model": settings.GROQ_MODEL,
            "base_url": settings.GROQ_BASE_URL,
            "phase": 2,
            "features": {
                "basic_hints": True,
                "code_analysis": True,
                "smart_hints": True,
                "intervention_detection": True
            }
        }
    except Exception as e:
        return {
            "configured": False,
            "error": str(e)
        }


# ===== PHASE 2: ADVANCED TUTORING ENDPOINTS =====

@router.post("/analyze")
async def analyze_code(request: AnalyzeCodeRequest):
    """
    Analyze student code using AST parsing
    
    Returns detailed insights about code structure, complexity, and issues
    """
    try:
        analyzer = CodeAnalyzer()
        
        if request.language == "python":
            result = analyzer.analyze_python(request.code)
            summary = analyzer.get_code_summary(request.code, request.language)
            
            return {
                "success": True,
                "language": request.language,
                "is_valid": result.is_valid,
                "summary": summary,
                "metrics": {
                    "functions": result.function_count,
                    "loops": result.loop_count,
                    "variables": result.variable_count,
                    "complexity": result.complexity_score,
                    "has_recursion": result.has_recursion
                },
                "issues": [issue.value for issue in result.issues],
                "syntax_errors": result.syntax_errors,
                "structure": result.code_structure
            }
        else:
            return {
                "success": False,
                "error": f"Language '{request.language}' not yet supported. Currently supports: python"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")


@router.post("/hint/smart")
async def generate_smart_hint(request: SmartHintRequest):
    """
    Generate intelligent hint based on full student context
    
    Uses state machine to decide intervention level:
    - Level 1: Socratic Question
    - Level 2: Conceptual Nudge  
    - Level 3: Pseudo-code
    - Level 4: Direct Hint
    """
    try:
        # Analyze code first
        analyzer = CodeAnalyzer()
        code_analysis = analyzer.analyze_python(request.student_code)
        
        # Build student context
        context = StudentContext(
            problem_description=request.problem_description,
            current_code=request.student_code,
            time_stuck=request.time_stuck,
            frustration_level=request.frustration_level,
            previous_hints=request.previous_hints_count,
            code_attempts=request.code_attempts
        )
        
        # Decide intervention strategy
        engine = TutoringEngine()
        decision = engine.decide_intervention(context)
        
        # Generate hint at appropriate level
        groq = get_groq_service()
        hint_gen = HintGenerator(groq)
        
        hint = await hint_gen.generate_hint(
            level=decision.hint_level,
            problem=request.problem_description,
            code=request.student_code,
            analysis={
                "function_count": code_analysis.function_count,
                "loop_count": code_analysis.loop_count,
                "issues": code_analysis.issues
            }
        )
        
        return {
            "success": True,
            "hint": hint,
            "hint_level": decision.hint_level.name,
            "hint_level_value": decision.hint_level.value,
            "should_intervene": decision.should_intervene,
            "intervention_reason": decision.reason,
            "urgency": decision.urgency,
            "code_analysis": {
                "is_valid": code_analysis.is_valid,
                "issues": [issue.value for issue in code_analysis.issues],
                "complexity": code_analysis.complexity_score
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart Hint Error: {str(e)}")


@router.post("/intervention/check")
async def check_intervention_needed(request: InterventionCheckRequest):
    """
    Check if intervention is needed (fast check without generating hint)
    
    Returns decision based on:
    - Time stuck
    - Frustration level
    - Previous attempts
    - Code quality
    """
    try:
        context = StudentContext(
            problem_description=request.problem_description,
            current_code=request.student_code,
            time_stuck=request.time_stuck,
            frustration_level=request.frustration_level,
            previous_hints=request.previous_hints,
            code_attempts=request.code_attempts
        )
        
        engine = TutoringEngine()
        decision = engine.decide_intervention(context)
        
        return {
            "success": True,
            "should_intervene": decision.should_intervene,
            "reason": decision.reason,
            "recommended_hint_level": decision.hint_level.name,
            "urgency": decision.urgency,
            "context": {
                "time_stuck": request.time_stuck,
                "frustration_level": request.frustration_level,
                "previous_hints": request.previous_hints
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intervention Check Error: {str(e)}")


# ===== PROBLEM GENERATOR ENDPOINTS (Teacher Tools) =====

@router.post("/generate-problem")
async def generate_problem(request: GenerateProblemRequest):
    """
    Generate a structured programming problem from natural language description.
    
    This is the "Teacher Tool" endpoint - allows educators to quickly create
    curriculum content by describing problems in plain English.
    
    **Example Request:**
    ```json
    {
        "raw_description": "Create a function that finds the longest palindrome substring in a given string",
        "language": "python",
        "difficulty": "medium",
        "num_test_cases": 5
    }
    ```
    
    **Returns:**
    - Complete problem specification with:
        - Formal problem statement
        - Starter code template
        - Test cases (visible + hidden)
        - Socratic-style hints
        - Concepts covered
    """
    try:
        generator = get_problem_generator()
        
        problem_spec = await generator.generate_problem_from_text(
            raw_description=request.raw_description,
            language=request.language,
            difficulty=request.difficulty,
            num_test_cases=request.num_test_cases
        )
        
        return {
            "success": True,
            "problem": {
                "title": problem_spec.title,
                "description": problem_spec.description,
                "difficulty": problem_spec.difficulty,
                "concepts": problem_spec.concepts,
                "starter_code": problem_spec.starter_code,
                "solution_template": problem_spec.solution_template,
                "test_cases": [
                    {
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                        "explanation": tc.explanation,
                        "is_hidden": tc.is_hidden
                    }
                    for tc in problem_spec.test_cases
                ],
                "hints": problem_spec.hints,
                "time_limit_seconds": problem_spec.time_limit_seconds,
                "memory_limit_mb": problem_spec.memory_limit_mb
            }
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Problem Generation Error: {str(e)}")


@router.post("/generate-test-cases")
async def generate_additional_test_cases(request: AdditionalTestCasesRequest):
    """
    Generate additional test cases for an existing problem.
    
    Useful when you need more edge case coverage or want to expand
    the test suite after the initial problem creation.
    
    **Returns:**
    - List of new test cases (typically marked as hidden for evaluation)
    """
    try:
        generator = get_problem_generator()
        
        # Convert existing test cases to TestCase objects
        from app.services.problem_generator import TestCase
        existing = [
            TestCase(
                input=tc["input"],
                expected_output=tc["expected_output"],
                explanation=tc.get("explanation", ""),
                is_hidden=tc.get("is_hidden", False)
            )
            for tc in request.existing_test_cases
        ]
        
        new_cases = await generator.generate_additional_test_cases(
            problem_description=request.problem_description,
            existing_test_cases=existing,
            num_additional=request.num_additional
        )
        
        return {
            "success": True,
            "new_test_cases": [
                {
                    "input": tc.input,
                    "expected_output": tc.expected_output,
                    "explanation": tc.explanation,
                    "is_hidden": tc.is_hidden
                }
                for tc in new_cases
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test Case Generation Error: {str(e)}")


