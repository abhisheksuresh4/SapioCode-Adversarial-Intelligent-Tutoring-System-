"""
Peer Learning API Routes

Endpoints for collaborative learning and student matching:
- /peer/profile - Create/update student profiles
- /peer/match - Find learning partners
- /peer/session - Manage collaborative sessions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.services.peer_learning import (
    peer_learning_service,
    SkillLevel,
    LearningStyle,
    SessionRole,
    SessionStatus
)


router = APIRouter(prefix="/peer", tags=["Peer Learning"])


# ============ Request/Response Models ============

class CreateProfileRequest(BaseModel):
    """Request to create student profile"""
    student_id: str
    name: str
    skill_level: str = Field(..., description="beginner, intermediate, advanced, expert")
    learning_style: str = Field(..., description="visual, auditory, kinesthetic, reading_writing")
    topics_mastered: List[str] = Field(default_factory=list)
    topics_learning: List[str] = Field(default_factory=list)
    preferred_role: str = Field(default="peer", description="learner, tutor, peer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "student123",
                "name": "Alice Johnson",
                "skill_level": "intermediate",
                "learning_style": "visual",
                "topics_mastered": ["variables", "loops", "functions"],
                "topics_learning": ["recursion", "data_structures"],
                "preferred_role": "peer"
            }
        }


class ProfileResponse(BaseModel):
    """Student profile response"""
    student_id: str
    name: str
    skill_level: str
    learning_style: str
    topics_mastered: List[str]
    topics_learning: List[str]
    preferred_role: str
    total_sessions: int
    average_rating: float
    created_at: datetime
    updated_at: datetime


class FindMatchRequest(BaseModel):
    """Request to find learning partners"""
    student_id: str
    topic: str
    max_matches: int = Field(default=5, ge=1, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "student123",
                "topic": "recursion",
                "max_matches": 5
            }
        }


class MatchResponse(BaseModel):
    """Match result"""
    student_id: str
    name: str
    skill_level: str
    score: float
    reasons: List[str]
    complementary_skills: List[str]
    shared_interests: List[str]


class StartSessionRequest(BaseModel):
    """Request to start peer session"""
    student1_id: str
    student2_id: str
    topic: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "student1_id": "student123",
                "student2_id": "student456",
                "topic": "recursion"
            }
        }


class SessionResponse(BaseModel):
    """Peer session response"""
    session_id: str
    student1_id: str
    student2_id: str
    topic: str
    student1_role: str
    student2_role: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: int


class EndSessionRequest(BaseModel):
    """Request to end session"""
    session_id: str
    student1_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    student2_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    notes: str = ""


# ============ Endpoints ============

@router.post("/profile", response_model=ProfileResponse)
async def create_profile(request: CreateProfileRequest):
    """
    Create or update a student profile for peer matching.
    
    This profile is used to find compatible learning partners based on:
    - Skill level (beginner to expert)
    - Learning style (visual, auditory, etc.)
    - Topics mastered and currently learning
    - Preferred role (learner, tutor, or peer)
    """
    try:
        # Convert string enums to enum types
        skill_level = SkillLevel(request.skill_level.lower())
        learning_style = LearningStyle(request.learning_style.lower())
        preferred_role = SessionRole(request.preferred_role.lower())
        
        profile = peer_learning_service.create_profile(
            student_id=request.student_id,
            name=request.name,
            skill_level=skill_level,
            learning_style=learning_style,
            topics_mastered=request.topics_mastered,
            topics_learning=request.topics_learning,
            preferred_role=preferred_role
        )
        
        return ProfileResponse(
            student_id=profile.student_id,
            name=profile.name,
            skill_level=profile.skill_level.value,
            learning_style=profile.learning_style.value,
            topics_mastered=profile.topics_mastered,
            topics_learning=profile.topics_learning,
            preferred_role=profile.preferred_role.value,
            total_sessions=profile.total_sessions,
            average_rating=profile.average_rating,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")


@router.get("/profile/{student_id}", response_model=ProfileResponse)
async def get_profile(student_id: str):
    """
    Get a student's profile by ID.
    """
    profile = peer_learning_service.get_profile(student_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return ProfileResponse(
        student_id=profile.student_id,
        name=profile.name,
        skill_level=profile.skill_level.value,
        learning_style=profile.learning_style.value,
        topics_mastered=profile.topics_mastered,
        topics_learning=profile.topics_learning,
        preferred_role=profile.preferred_role.value,
        total_sessions=profile.total_sessions,
        average_rating=profile.average_rating,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.post("/match", response_model=List[MatchResponse])
async def find_matches(request: FindMatchRequest):
    """
    Find compatible learning partners for a student.
    
    The matching algorithm considers:
    - Complementary skill levels (e.g., beginner + intermediate)
    - Topic overlap (what they can teach each other)
    - Learning style compatibility
    - Previous session ratings
    
    Returns a ranked list of potential partners with match scores.
    """
    # Verify student exists
    profile = peer_learning_service.get_profile(request.student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    try:
        matches = peer_learning_service.find_matches(
            student_id=request.student_id,
            topic=request.topic,
            max_matches=request.max_matches
        )
        
        # Convert to response format
        results = []
        for match in matches:
            matched_profile = peer_learning_service.get_profile(match.student_id)
            if matched_profile:
                results.append(MatchResponse(
                    student_id=match.student_id,
                    name=matched_profile.name,
                    skill_level=matched_profile.skill_level.value,
                    score=match.score,
                    reasons=match.reasons,
                    complementary_skills=match.complementary_skills,
                    shared_interests=match.shared_interests
                ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest):
    """
    Start a new peer learning session.
    
    This creates an active collaborative session between two students.
    Roles (tutor/learner/peer) are automatically assigned based on
    skill levels and topic mastery.
    """
    try:
        session = peer_learning_service.start_session(
            student1_id=request.student1_id,
            student2_id=request.student2_id,
            topic=request.topic
        )
        
        return SessionResponse(
            session_id=session.session_id,
            student1_id=session.student1_id,
            student2_id=session.student2_id,
            topic=session.topic,
            student1_role=session.student1_role.value,
            student2_role=session.student2_role.value,
            status=session.status.value,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_minutes=session.duration_minutes
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session start failed: {str(e)}")


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get details of a peer learning session.
    """
    session = peer_learning_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session.session_id,
        student1_id=session.student1_id,
        student2_id=session.student2_id,
        topic=session.topic,
        student1_role=session.student1_role.value,
        student2_role=session.student2_role.value,
        status=session.status.value,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes
    )


@router.post("/session/end", response_model=SessionResponse)
async def end_session(request: EndSessionRequest):
    """
    End a peer learning session.
    
    Optionally provide ratings (1-5) from both students to help
    improve future matching quality.
    """
    session = peer_learning_service.end_session(
        session_id=request.session_id,
        student1_rating=request.student1_rating,
        student2_rating=request.student2_rating,
        notes=request.notes
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session.session_id,
        student1_id=session.student1_id,
        student2_id=session.student2_id,
        topic=session.topic,
        student1_role=session.student1_role.value,
        student2_role=session.student2_role.value,
        status=session.status.value,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes
    )



@router.post("/invite", response_model=SessionResponse)
async def invite_student(
    request: StartSessionRequest  # We can reuse this model
):
    """
    Send a manual session invite to a specific student.
    Returns session in PENDING state.
    """
    try:
        session = peer_learning_service.create_invite(
            requester_id=request.student1_id,
            target_id=request.student2_id,
            topic=request.topic
        )
        return SessionResponse(
            session_id=session.session_id,
            student1_id=session.student1_id,
            student2_id=session.student2_id,
            topic=session.topic,
            student1_role=session.student1_role.value,
            student2_role=session.student2_role.value,
            status=session.status.value,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_minutes=session.duration_minutes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invite/{session_id}/accept", response_model=SessionResponse)
async def accept_invite(session_id: str):
    """
    Accept a pending session invite.
    Changes status to ACTIVE.
    """
    session = peer_learning_service.respond_to_invite(session_id, accept=True)
    if not session:
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    
    return SessionResponse(
        session_id=session.session_id,
        student1_id=session.student1_id,
        student2_id=session.student2_id,
        topic=session.topic,
        student1_role=session.student1_role.value,
        student2_role=session.student2_role.value,
        status=session.status.value,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes
    )


@router.post("/invite/{session_id}/reject", response_model=SessionResponse)
async def reject_invite(session_id: str):
    """
    Reject a session invite.
    Changes status to REJECTED.
    """
    session = peer_learning_service.respond_to_invite(session_id, accept=False)
    if not session:
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    
    return SessionResponse(
        session_id=session.session_id,
        student1_id=session.student1_id,
        student2_id=session.student2_id,
        topic=session.topic,
        student1_role=session.student1_role.value,
        student2_role=session.student2_role.value,
        status=session.status.value,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes
    )


@router.get("/sessions/{student_id}")
async def get_student_sessions(
    student_id: str,
    status: Optional[str] = None
):
    """
    Get all sessions for a student.
    
    Optionally filter by status: active, completed, cancelled
    """
    try:
        status_filter = SessionStatus(status.lower()) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    sessions = peer_learning_service.get_student_sessions(
        student_id=student_id,
        status=status_filter
    )
    
    return {
        "student_id": student_id,
        "total_sessions": len(sessions),
        "sessions": [
            SessionResponse(
                session_id=s.session_id,
                student1_id=s.student1_id,
                student2_id=s.student2_id,
                topic=s.topic,
                student1_role=s.student1_role.value,
                student2_role=s.student2_role.value,
                status=s.status.value,
                started_at=s.started_at,
                ended_at=s.ended_at,
                duration_minutes=s.duration_minutes
            )
            for s in sessions
        ]
    }


@router.get("/health")
async def peer_health():
    """Health check for peer learning subsystem"""
    return {
        "status": "healthy",
        "total_profiles": len(peer_learning_service.profiles),
        "active_sessions": len([
            s for s in peer_learning_service.sessions.values()
            if s.status == SessionStatus.ACTIVE
        ])
    }
