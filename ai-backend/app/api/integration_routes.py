"""
Integration API Routes — Full SapioCode Pipeline Endpoints

These endpoints connect the React frontend to the unified pipeline:
  POST /api/integration/submit       → Full code submission pipeline
  POST /api/integration/hint         → Standalone Socratic hint
  POST /api/integration/hint-graph   → LangGraph-powered Socratic hint
  POST /api/integration/affect       → Process facial expression data
  POST /api/integration/viva-complete → Forward viva result to BKT
  GET  /api/integration/mastery/{id} → Student mastery snapshot
  GET  /api/integration/status       → Service health check
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.integration_bridge import (
    get_integration_bridge,
    CodeSubmission,
    CognitiveState,
)
from app.services.affect_adapter import get_affect_adapter
from app.services.bkt_local import get_local_bkt
from app.services.langgraph_tutoring import (
    get_tutoring_graph,
    record_student_message,
    TutoringState,
)

router = APIRouter()


# ═══════════════════════════════════════════════════
# Request / Response Models
# ═══════════════════════════════════════════════════

class SubmitCodeRequest(BaseModel):
    """Unified submission request from the frontend."""
    student_id: str = Field(..., description="Student's unique ID")
    submission_id: str = Field(..., description="Unique submission ID")
    problem_description: str = Field(..., description="Problem statement")
    code: str = Field(..., description="Student's code")
    language: str = Field(default="python", description="Programming language")
    stdin: str = Field(default="", description="Optional stdin input")
    concepts: List[str] = Field(default=[], description="Concepts this problem tests e.g. ['loops','recursion']")

    # Student struggle context
    time_stuck: int = Field(default=0, description="Seconds student has been stuck")
    previous_hints: int = Field(default=0, description="Hints already given this session")
    code_attempts: int = Field(default=0, description="Number of run attempts")

    # Cognitive state from Role 3's Face-API.js perception
    frustration: float = Field(default=0.1, ge=0.0, le=1.0)
    engagement: float = Field(default=0.7, ge=0.0, le=1.0)
    confusion: float = Field(default=0.2, ge=0.0, le=1.0)
    boredom: float = Field(default=0.0, ge=0.0, le=1.0)


class HintRequest(BaseModel):
    """Request for a Socratic hint without full submission."""
    student_id: str = Field(default="anonymous")
    problem_description: str
    code: str
    time_stuck: int = 60
    previous_hints: int = 0
    frustration: float = Field(default=0.1, ge=0.0, le=1.0)
    engagement: float = Field(default=0.7, ge=0.0, le=1.0)
    confusion: float = Field(default=0.2, ge=0.0, le=1.0)
    boredom: float = Field(default=0.0, ge=0.0, le=1.0)


class AffectUpdateRequest(BaseModel):
    """
    Process raw Face-API.js expressions OR pre-computed cognitive state.
    The frontend sends this every ~2 seconds.
    """
    student_id: str

    # Option A: Raw Face-API.js expressions
    raw_expressions: Optional[dict] = Field(
        default=None,
        description="Raw face-api.js output: {happy, sad, angry, fearful, surprised, neutral}"
    )

    # Option B: Pre-computed cognitive state
    cognitive_state: Optional[dict] = Field(
        default=None,
        description="Pre-computed: {engagement, confusion, frustration, boredom}"
    )


class VivaCompletedRequest(BaseModel):
    """Called after Viva Voce completes to update BKT with understanding data."""
    student_id: str
    submission_id: str
    viva_verdict: str = Field(..., description="PASS | FAIL | PARTIAL")
    average_score: float = Field(..., ge=0.0, le=1.0)
    concepts: List[str] = Field(default=[], description="Concepts tested in viva")
    frustration: float = Field(default=0.1, ge=0.0, le=1.0)
    engagement: float = Field(default=0.7, ge=0.0, le=1.0)


# ═══════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════

@router.post("/submit")
async def submit_code(request: SubmitCodeRequest):
    """
    **Unified code submission endpoint — the heart of SapioCode.**

    Orchestrates the full pipeline:
    1. Executes code via Role 1 (backend:8000/run)
    2. Analyzes AST (Role 2)
    3. Processes affect data (Role 3 math)
    4. Updates BKT mastery locally + syncs to Role 3 Neo4j
    5. Decides Socratic intervention based on mastery + affect
    6. Returns unified feedback

    **Example:**
    ```json
    {
        "student_id": "s001",
        "submission_id": "sub_123",
        "problem_description": "Reverse a linked list",
        "code": "def reverse(head):\\n    prev = None\\n    ...",
        "concepts": ["linked_lists", "recursion"],
        "time_stuck": 120,
        "frustration": 0.6,
        "engagement": 0.4
    }
    ```
    """
    try:
        bridge = get_integration_bridge()

        submission = CodeSubmission(
            student_id=request.student_id,
            submission_id=request.submission_id,
            problem_description=request.problem_description,
            code=request.code,
            language=request.language,
            stdin=request.stdin,
            concepts=request.concepts,
            time_stuck=request.time_stuck,
            previous_hints=request.previous_hints,
            code_attempts=request.code_attempts,
        )

        cognitive = CognitiveState(
            frustration=request.frustration,
            engagement=request.engagement,
            confusion=request.confusion,
            boredom=request.boredom,
        )

        feedback = await bridge.process_submission(submission, cognitive)

        return {"success": True, **feedback.to_dict()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.post("/hint")
async def get_socratic_hint(request: HintRequest):
    """
    Get a Socratic hint without running the full submission pipeline.

    Used when the student clicks "Get Hint" during coding.
    Takes affect data into account for tone adjustment.
    """
    try:
        bridge = get_integration_bridge()

        # Feed affect data so hints reflect current emotional state
        affect = get_affect_adapter()
        affect.process_cognitive_state(request.student_id, {
            "frustration": request.frustration,
            "engagement": request.engagement,
            "confusion": request.confusion,
            "boredom": request.boredom,
        })

        result = await bridge.generate_standalone_hint(
            student_id=request.student_id,
            problem_description=request.problem_description,
            code=request.code,
            time_stuck=request.time_stuck,
            previous_hints=request.previous_hints,
        )

        return {"success": True, **result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hint error: {str(e)}")


@router.post("/affect")
async def update_affect(request: AffectUpdateRequest):
    """
    Process facial expression data from the frontend.

    The frontend (Face-API.js) sends this every ~2 seconds.
    Accepts EITHER raw expressions OR pre-computed cognitive state.

    Returns the smoothed cognitive state + any intervention decision.
    """
    adapter = get_affect_adapter()

    if request.raw_expressions:
        smoothed = adapter.process_raw_expressions(
            request.student_id,
            request.raw_expressions
        )
    elif request.cognitive_state:
        smoothed = adapter.process_cognitive_state(
            request.student_id,
            request.cognitive_state
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'raw_expressions' or 'cognitive_state'"
        )

    intervention = adapter.should_intervene(request.student_id)

    return {
        "student_id": request.student_id,
        "smoothed_state": smoothed,
        "intervention": intervention,
    }


@router.post("/viva-complete")
async def viva_completed(request: VivaCompletedRequest):
    """
    Called after a Viva Voce session completes.

    Updates BKT with the viva result — this tracks UNDERSTANDING,
    not just code correctness:
      PASS   → BKT treats as correct  (student understands the concept)
      FAIL   → BKT treats as incorrect (code worked but no understanding)
      PARTIAL → BKT treats as correct only if score >= 0.6
    """
    try:
        bridge = get_integration_bridge()
        bkt = get_local_bkt()

        # Determine if student demonstrated understanding
        understood = (
            request.viva_verdict == "PASS"
            or (request.viva_verdict == "PARTIAL" and request.average_score >= 0.6)
        )

        cognitive = {
            "frustration": request.frustration,
            "engagement": request.engagement,
            "confusion": 0.0 if understood else 0.5,
            "boredom": 0.0,
        }

        # Update local BKT with viva result
        concepts = request.concepts or ["general_programming"]
        mastery_results = bkt.process_submission(
            student_id=request.student_id,
            concepts=concepts,
            correct=understood,
            cognitive_state=cognitive,
        )

        # Sync to Role 3's Neo4j
        neo4j_synced = await bridge._sync_to_role3_bkt(
            student_id=request.student_id,
            submission_id=f"{request.submission_id}_viva",
            correct=understood,
            cognitive_state=cognitive,
        )

        return {
            "success": True,
            "viva_verdict": request.viva_verdict,
            "understanding_confirmed": understood,
            "mastery_updates": mastery_results,
            "synced_to_neo4j": neo4j_synced,
            "message": (
                "Student demonstrated understanding — mastery updated positively"
                if understood else
                "Student could not explain code — mastery flagged for review"
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Viva BKT error: {str(e)}")


@router.get("/mastery/{student_id}")
async def get_student_mastery(student_id: str):
    """
    Get a student's current mastery snapshot.

    Returns mastery for all attempted concepts + weakest areas.
    Used by:
    - Curriculum navigator (lock/unlock nodes)
    - Teacher dashboard (class overview)
    - Tutoring engine (hint level decisions)
    """
    bkt = get_local_bkt()
    summary = bkt.get_student_summary(student_id)
    affect = get_affect_adapter()
    affect_summary = affect.get_student_affect_summary(student_id)

    return {
        "student_id": student_id,
        "mastery": summary,
        "affect": affect_summary,
    }


@router.get("/hint-history/{student_id}")
async def get_hint_history(student_id: str):
    """
    Get all AI hints given to a student.
    Used by the teacher dashboard to review AI-student interactions.
    """
    bridge = get_integration_bridge()
    history = bridge.get_hint_history(student_id)
    return {
        "student_id": student_id,
        "hint_count": len(history),
        "hints": history,
    }


@router.post("/hint-graph")
async def get_hint_via_langgraph(request: HintRequest):
    """
    **LangGraph-powered Socratic hint.**

    Uses a real LangGraph StateGraph with conditional edges:
      - frustration > 0.7  → gentle path (empathetic, sub-problem decomposition)
      - bored + high mastery → challenge path (optimization, edge cases)
      - otherwise          → Socratic path (guiding questions)

    AST analysis flows through every node; conversation memory is maintained.
    """
    try:
        graph = get_tutoring_graph()

        # Record student's code as a conversation turn
        record_student_message(request.student_id, request.code[:500])

        initial_state: TutoringState = {
            "student_id": request.student_id,
            "problem_description": request.problem_description,
            "code": request.code,
            "time_stuck": request.time_stuck,
            "previous_hints": request.previous_hints,
            "frustration": request.frustration,
            "engagement": request.engagement,
            "confusion": request.confusion,
            "boredom": request.boredom,
        }

        result = await graph.ainvoke(initial_state)

        return {
            "success": True,
            "engine": "langgraph",
            **(result.get("response", {})),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph hint error: {str(e)}",
        )


@router.get("/status")
async def integration_status():
    """
    Health check — reports connectivity to Role 1 and Role 3.
    """
    import httpx
    from app.services.integration_bridge import EXECUTION_BACKEND_URL, BKT_BACKEND_URL

    role1_status = "unknown"
    role3_status = "unknown"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{EXECUTION_BACKEND_URL}/")
            role1_status = "online" if r.status_code == 200 else "error"
    except Exception:
        role1_status = "offline"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{BKT_BACKEND_URL}/")
            role3_status = "online" if r.status_code == 200 else "error"
    except Exception:
        role3_status = "offline"

    return {
        "role2_ai_engine": "online",
        "role1_execution_backend": role1_status,
        "role3_bkt_engine": role3_status,
        "local_bkt_fallback": "active",
        "integration_ready": True,
        "note": (
            "Pipeline works even if Role 1/3 are offline — "
            "local execution fallback + local BKT engine active"
        ),
    }
