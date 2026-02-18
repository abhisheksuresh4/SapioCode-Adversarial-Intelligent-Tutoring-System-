"""
Teacher Dashboard API — Phase 4

Endpoints:
  GET  /api/teacher/class-pulse          — live class snapshot
  GET  /api/teacher/at-risk              — students flagged as at-risk
  GET  /api/teacher/student/{id}/profile — full breakdown per student
  GET  /api/teacher/student/{id}/chat-logs — hint conversation history
  GET  /api/teacher/mastery-heatmap      — concept × student mastery grid
  GET  /api/teacher/students             — list all tracked student IDs
  POST /api/teacher/generate-problem     — AI-generated problem from description
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.services.teacher_analytics import get_teacher_analytics
from app.services.problem_generator import get_problem_generator

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────


def _analytics():
    return get_teacher_analytics()


# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get("/class-pulse", summary="Live classroom snapshot")
async def class_pulse() -> Dict[str, Any]:
    """
    Returns a real-time snapshot of the whole class:
    - active student count
    - average mastery / frustration / engagement
    - how many students are at risk
    - concept the class is struggling with most
    """
    pulse = _analytics().get_class_pulse()
    return {
        "timestamp": pulse.timestamp,
        "active_students": pulse.active_students,
        "average_mastery": pulse.average_mastery,
        "average_frustration": pulse.average_frustration,
        "average_engagement": pulse.average_engagement,
        "at_risk_count": pulse.at_risk_count,
        "most_struggled_concept": pulse.most_struggled_concept,
    }


@router.get("/at-risk", summary="Students flagged as at-risk")
async def at_risk_students() -> List[Dict[str, Any]]:
    """
    Returns all students classified as medium or high risk.
    Sorted: high-risk first, then by frustration (descending).

    Risk factors:
      - overall mastery < 45 %
      - frustration > 65 %
      - 6 or more hints received in this session
    """
    profiles = _analytics().get_at_risk_students()
    return [
        {
            "student_id": p.student_id,
            "risk_level": p.risk_level,
            "risk_reason": p.risk_reason,
            "overall_mastery": p.overall_mastery,
            "frustration": p.frustration,
            "engagement": p.engagement,
            "total_hints_received": p.total_hints_received,
            "weak_concepts": p.weak_concepts,
        }
        for p in profiles
    ]


@router.get("/student/{student_id}/profile", summary="Full student profile")
async def student_profile(student_id: str) -> Dict[str, Any]:
    """
    Detailed breakdown for one student:
    - BKT mastery per concept
    - latest affect state (frustration, engagement, confusion, boredom)
    - total hints received
    - weak concepts
    - risk classification
    """
    known = _analytics().get_all_students()
    if student_id not in known:
        raise HTTPException(
            status_code=404,
            detail=f"Student '{student_id}' not found. "
                   f"Known students: {known[:10]}",
        )
    return _analytics().get_student_profile(student_id)


@router.get("/student/{student_id}/chat-logs", summary="Tutoring conversation history")
async def chat_logs(student_id: str) -> Dict[str, Any]:
    """
    Returns the full hint / tutoring conversation for a student.
    Each entry: { timestamp, hint_level, teaching_focus, hint_text }.

    Teachers can use this to review what hints were given and whether
    the tutoring strategy was effective.
    """
    logs = _analytics().get_chat_logs(student_id)
    return {
        "student_id": student_id,
        "total_hints": len(logs),
        "chat_log": logs,
    }


@router.get("/mastery-heatmap", summary="Concept mastery heatmap")
async def mastery_heatmap() -> Dict[str, Any]:
    """
    Returns a grid suitable for rendering as a heatmap:
      rows = students
      columns = concepts
      values = p(L) mastery probability (0-1)

    Low values (red) indicate concepts the class needs more work on.
    """
    rows = _analytics().get_mastery_heatmap()

    # Collect all concept names for consistent column ordering
    all_concepts: set = set()
    for row in rows:
        all_concepts.update(row.concept_masteries.keys())
    concepts_sorted = sorted(all_concepts)

    return {
        "concepts": concepts_sorted,
        "students": [
            {
                "student_id": row.student_id,
                "masteries": {
                    c: row.concept_masteries.get(c, 0.0)
                    for c in concepts_sorted
                },
            }
            for row in rows
        ],
    }


@router.get("/students", summary="List all tracked students")
async def list_students() -> Dict[str, Any]:
    """Returns the list of all student IDs the AI engine has seen."""
    ids = _analytics().get_all_students()
    return {"count": len(ids), "student_ids": ids}


# ═══════════════════════════════════════════════════════════════
# Problem Generation for Teachers
# ═══════════════════════════════════════════════════════════════

class GenerateProblemRequest(BaseModel):
    """Teacher provides a description, AI generates a full problem spec."""
    description: str = Field(
        ...,
        description="Natural language problem description, e.g. 'binary search on a sorted array'",
    )
    difficulty: str = Field(
        default="medium",
        description="Target difficulty: easy | medium | hard",
    )
    concepts: List[str] = Field(
        default=[],
        description="Concepts to test, e.g. ['recursion', 'arrays']",
    )
    num_test_cases: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of test cases to generate",
    )


@router.post("/generate-problem", summary="AI-generate a problem from description")
async def generate_problem(request: GenerateProblemRequest) -> Dict[str, Any]:
    """
    Teacher describes a problem in natural language, and the AI generates:
      - Full problem specification (title, description, constraints)
      - Sample test cases with expected inputs/outputs
      - Difficulty classification
      - Related concepts

    **Example request:**
    ```json
    {
        "description": "Write a function that finds the longest common subsequence of two strings",
        "difficulty": "hard",
        "concepts": ["dynamic_programming", "strings"],
        "num_test_cases": 4
    }
    ```
    """
    try:
        generator = get_problem_generator()
        problem = await generator.generate_problem_from_text(
            raw_description=request.description,
            difficulty=request.difficulty,
        )

        # Generate additional test cases if requested
        if request.num_test_cases > len(problem.test_cases):
            extra = await generator.generate_additional_test_cases(
                problem_description=problem.description,
                existing_test_cases=problem.test_cases,
                num_additional=request.num_test_cases - len(problem.test_cases),
            )
            problem.test_cases.extend(extra)

        return {
            "success": True,
            "problem": {
                "title": problem.title,
                "description": problem.description,
                "difficulty": problem.difficulty,
                "concepts": problem.concepts or request.concepts,
                "starter_code": problem.starter_code,
                "solution_template": problem.solution_template,
                "hints": problem.hints,
                "test_cases": [
                    {
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                        "explanation": tc.explanation,
                        "is_hidden": tc.is_hidden,
                    }
                    for tc in problem.test_cases
                ],
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Problem generation failed: {str(e)}",
        )
