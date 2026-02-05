"""
Viva Voce API Routes

Endpoints for the oral examination system:
- /viva/start - Start a new Viva session
- /viva/question - Get current question
- /viva/transcribe - Transcribe audio to text
- /viva/answer - Submit answer for evaluation
- /viva/verdict - Get final verdict
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import uuid

from app.services.whisper_service import whisper_service, TranscriptionStatus
from app.services.viva_engine import viva_engine, VivaVerdict


router = APIRouter(prefix="/viva", tags=["Viva Voce"])


# ============ Request/Response Models ============

class StartVivaRequest(BaseModel):
    """Request to start a Viva session"""
    student_id: str
    code: str
    num_questions: int = 3
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "student123",
                "code": "def add(a, b):\n    return a + b",
                "num_questions": 3
            }
        }


class StartVivaResponse(BaseModel):
    """Response after starting Viva session"""
    session_id: str
    total_questions: int
    first_question: str
    code_analysis: dict


class QuestionResponse(BaseModel):
    """Current question details"""
    question_number: int
    total_questions: int
    question_id: str
    question_text: str
    question_type: str
    target_code: Optional[str]
    target_line: Optional[int]


class TranscriptionResponse(BaseModel):
    """Response from audio transcription"""
    success: bool
    text: Optional[str]
    duration_seconds: Optional[float]
    confidence: Optional[float]
    error: Optional[str]


class SubmitAnswerRequest(BaseModel):
    """Submit an answer (already transcribed)"""
    session_id: str
    transcribed_text: str
    audio_duration_seconds: float = 10.0


class AnswerEvaluationResponse(BaseModel):
    """Evaluation of submitted answer"""
    score: float
    is_acceptable: bool
    matched_concepts: List[str]
    missing_concepts: List[str]
    feedback: str
    has_more_questions: bool
    next_question: Optional[str]


class VerdictResponse(BaseModel):
    """Final Viva verdict"""
    verdict: str
    average_score: float
    message: str
    questions_answered: int
    question_breakdown: List[dict]
    improvement_areas: List[str]


# ============ Endpoints ============

@router.post("/start", response_model=StartVivaResponse)
async def start_viva_session(request: StartVivaRequest):
    """
    Start a new Viva Voce examination session.
    
    This analyzes the student's code and generates targeted questions
    that will verify their understanding.
    """
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    try:
        # Start the Viva session
        session = viva_engine.start_session(
            session_id=session_id,
            student_id=request.student_id,
            code=request.code,
            num_questions=request.num_questions
        )
        
        # Get first question
        first_q = session.questions[0] if session.questions else None
        
        return StartVivaResponse(
            session_id=session_id,
            total_questions=len(session.questions),
            first_question=first_q.question_text if first_q else "No questions generated",
            code_analysis={
                "functions_found": session.analysis.code_structure.get("functions", []),
                "loops_found": session.analysis.loop_count,
                "has_recursion": session.analysis.has_recursion,
                "issues": [
                    {"type": issue.value, "message": issue.value.replace("_", " ")}
                    for issue in session.analysis.issues
                ]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Viva: {str(e)}")


@router.get("/question/{session_id}", response_model=QuestionResponse)
async def get_current_question(session_id: str):
    """
    Get the current question for an active Viva session.
    
    Returns the question the student should answer next.
    """
    session = viva_engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_q = viva_engine.get_current_question(session_id)
    if not current_q:
        raise HTTPException(status_code=400, detail="No more questions - get verdict")
    
    return QuestionResponse(
        question_number=session.current_question_index + 1,
        total_questions=len(session.questions),
        question_id=current_q.id,
        question_text=current_q.question_text,
        question_type=current_q.question_type.value,
        target_code=current_q.target_code,
        target_line=current_q.target_line
    )


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Transcribe audio file to text using Whisper.
    
    Accepts audio file (webm, mp3, wav, etc.) and returns transcription.
    Use this endpoint to convert student's verbal response to text.
    """
    # Verify session exists
    if session_id not in viva_engine.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Transcribe
        result = await whisper_service.transcribe_audio(
            audio_data=audio_data,
            filename=audio.filename or "audio.webm"
        )
        
        if result.status == TranscriptionStatus.SUCCESS:
            return TranscriptionResponse(
                success=True,
                text=result.text,
                duration_seconds=result.duration_seconds,
                confidence=result.confidence,
                error=None
            )
        else:
            return TranscriptionResponse(
                success=False,
                text=None,
                duration_seconds=None,
                confidence=None,
                error=result.error_message
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/transcribe/base64", response_model=TranscriptionResponse)
async def transcribe_audio_base64(
    session_id: str,
    audio_base64: str,
    filename: str = "audio.webm"
):
    """
    Transcribe base64-encoded audio to text.
    
    Alternative to file upload - accepts base64 string directly.
    Useful when frontend sends audio as data URL.
    """
    # Verify session exists
    if session_id not in viva_engine.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        result = await whisper_service.transcribe_base64(
            base64_audio=audio_base64,
            filename=filename
        )
        
        if result.status == TranscriptionStatus.SUCCESS:
            return TranscriptionResponse(
                success=True,
                text=result.text,
                duration_seconds=result.duration_seconds,
                confidence=result.confidence,
                error=None
            )
        else:
            return TranscriptionResponse(
                success=False,
                text=None,
                duration_seconds=None,
                confidence=None,
                error=result.error_message
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/answer", response_model=AnswerEvaluationResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit a transcribed answer for evaluation.
    
    The answer will be semantically compared against the code
    to verify student understanding.
    """
    try:
        # Submit and evaluate
        evaluation = await viva_engine.submit_answer(
            session_id=request.session_id,
            transcribed_text=request.transcribed_text,
            audio_duration=request.audio_duration_seconds
        )
        
        # Check if there are more questions
        next_q = viva_engine.get_current_question(request.session_id)
        
        return AnswerEvaluationResponse(
            score=evaluation.score,
            is_acceptable=evaluation.is_acceptable,
            matched_concepts=evaluation.matched_concepts,
            missing_concepts=evaluation.missing_concepts,
            feedback=evaluation.feedback,
            has_more_questions=next_q is not None,
            next_question=next_q.question_text if next_q else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/verdict/{session_id}", response_model=VerdictResponse)
async def get_verdict(session_id: str):
    """
    Get the final Viva verdict for a completed session.
    
    Returns overall score, verdict (pass/weak/fail), and improvement areas.
    """
    result = viva_engine.get_verdict(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    if result["verdict"] == VivaVerdict.INCONCLUSIVE.value:
        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )
    
    return VerdictResponse(
        verdict=result["verdict"],
        average_score=result["average_score"],
        message=result["message"],
        questions_answered=result["questions_answered"],
        question_breakdown=result["question_breakdown"],
        improvement_areas=result["improvement_areas"]
    )


@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """
    End and cleanup a Viva session.
    """
    if session_id in viva_engine.sessions:
        del viva_engine.sessions[session_id]
        return {"message": "Session ended", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/health")
async def viva_health():
    """Health check for Viva subsystem"""
    return {
        "status": "healthy",
        "active_sessions": len(viva_engine.sessions),
        "whisper_available": whisper_service.api_key is not None
    }
