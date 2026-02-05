"""
Peer Learning Service for SapioCode

This module implements the peer learning system that matches students
for collaborative learning based on skill levels and learning styles.

Components:
1. StudentProfile - Tracks student skills, preferences, learning style
2. MatchingAlgorithm - Finds compatible learning partners
3. PeerSession - Manages collaborative learning sessions
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class SkillLevel(Enum):
    """Student skill levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStyle(Enum):
    """Learning style preferences"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"


class SessionRole(Enum):
    """Role in peer learning session"""
    LEARNER = "learner"
    TUTOR = "tutor"
    PEER = "peer"


class SessionStatus(Enum):
    """Status of peer learning session"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING = "pending"  # For manual invites
    REJECTED = "rejected"


@dataclass
class StudentProfile:
    """Student profile for peer matching"""
    student_id: str
    name: str
    skill_level: SkillLevel
    learning_style: LearningStyle
    topics_mastered: List[str] = field(default_factory=list)
    topics_learning: List[str] = field(default_factory=list)
    preferred_role: SessionRole = SessionRole.PEER
    availability: List[str] = field(default_factory=list)  # Time slots
    total_sessions: int = 0
    average_rating: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MatchScore:
    """Score for a potential peer match"""
    student_id: str
    score: float
    reasons: List[str]
    complementary_skills: List[str]
    shared_interests: List[str]


@dataclass
class PeerSession:
    """Collaborative learning session"""
    session_id: str
    student1_id: str
    student2_id: str
    topic: str
    student1_role: SessionRole
    student2_role: SessionRole
    status: SessionStatus
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_minutes: int = 0
    code_shared: Optional[str] = None
    notes: str = ""
    student1_rating: Optional[float] = None
    student2_rating: Optional[float] = None


class PeerLearningService:
    """
    Service for managing peer learning and student matching.
    
    Features:
    - Student profiling based on skills and preferences
    - Intelligent matching algorithm
    - Session management
    """
    
    def __init__(self):
        # In-memory storage (will be replaced with database)
        self.profiles: Dict[str, StudentProfile] = {}
        self.sessions: Dict[str, PeerSession] = {}
    
    def create_profile(
        self,
        student_id: str,
        name: str,
        skill_level: SkillLevel,
        learning_style: LearningStyle,
        topics_mastered: List[str] = None,
        topics_learning: List[str] = None,
        preferred_role: SessionRole = SessionRole.PEER
    ) -> StudentProfile:
        """
        Create or update a student profile.
        
        Args:
            student_id: Unique student identifier
            name: Student name
            skill_level: Current skill level
            learning_style: Preferred learning style
            topics_mastered: List of mastered topics
            topics_learning: List of topics currently learning
            preferred_role: Preferred role in sessions
            
        Returns:
            Created StudentProfile
        """
        profile = StudentProfile(
            student_id=student_id,
            name=name,
            skill_level=skill_level,
            learning_style=learning_style,
            topics_mastered=topics_mastered or [],
            topics_learning=topics_learning or [],
            preferred_role=preferred_role
        )
        
        self.profiles[student_id] = profile
        return profile
    
    def get_profile(self, student_id: str) -> Optional[StudentProfile]:
        """Get student profile by ID"""
        return self.profiles.get(student_id)
    
    def update_profile(
        self,
        student_id: str,
        **updates
    ) -> Optional[StudentProfile]:
        """
        Update student profile.
        
        Args:
            student_id: Student to update
            **updates: Fields to update
            
        Returns:
            Updated profile or None if not found
        """
        profile = self.profiles.get(student_id)
        if not profile:
            return None
        
        # Update allowed fields
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        return profile
    
    def find_matches(
        self,
        student_id: str,
        topic: str,
        max_matches: int = 5
    ) -> List[MatchScore]:
        """
        Find compatible learning partners for a student.
        
        Matching criteria:
        1. Complementary skill levels (beginner + intermediate/advanced)
        2. Shared learning topics
        3. Compatible learning styles
        4. Availability overlap
        5. Previous session ratings
        
        Args:
            student_id: Student looking for a match
            topic: Topic they want to learn/teach
            max_matches: Maximum number of matches to return
            
        Returns:
            List of MatchScore objects, sorted by score
        """
        requester = self.profiles.get(student_id)
        if not requester:
            return []
        
        matches = []
        
        for candidate_id, candidate in self.profiles.items():
            # Skip self
            if candidate_id == student_id:
                continue
            
            score = 0.0
            reasons = []
            complementary_skills = []
            shared_interests = []
            
            # 1. Skill level complementarity (40% weight)
            skill_score = self._calculate_skill_compatibility(
                requester.skill_level,
                candidate.skill_level,
                requester.preferred_role
            )
            score += skill_score * 0.4
            if skill_score > 0.5:
                reasons.append("Compatible skill levels")
            
            # 2. Topic overlap (30% weight)
            topic_score = self._calculate_topic_overlap(
                requester, candidate, topic
            )
            score += topic_score * 0.3
            if topic_score > 0.5:
                # Find shared topics
                shared = set(requester.topics_learning) & set(candidate.topics_mastered)
                shared_interests.extend(list(shared)[:3])
                
                # Find complementary skills
                comp = set(requester.topics_learning) & set(candidate.topics_mastered)
                complementary_skills.extend(list(comp)[:3])
                
                if shared:
                    reasons.append(f"Shared interest in {len(shared)} topics")
                if comp:
                    reasons.append(f"Can help with {len(comp)} topics")
            
            # 3. Learning style compatibility (15% weight)
            style_score = 1.0 if requester.learning_style == candidate.learning_style else 0.5
            score += style_score * 0.15
            if style_score == 1.0:
                reasons.append("Same learning style")
            
            # 4. Rating history (15% weight)
            rating_score = min(candidate.average_rating / 5.0, 1.0)
            score += rating_score * 0.15
            if candidate.average_rating >= 4.0:
                reasons.append(f"High rating ({candidate.average_rating:.1f}/5.0)")
            
            # Only include matches with score > 0.3
            if score > 0.3:
                matches.append(MatchScore(
                    student_id=candidate_id,
                    score=score,
                    reasons=reasons,
                    complementary_skills=complementary_skills,
                    shared_interests=shared_interests
                ))
        
        # Sort by score descending
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:max_matches]
    
    def _calculate_skill_compatibility(
        self,
        requester_level: SkillLevel,
        candidate_level: SkillLevel,
        preferred_role: SessionRole
    ) -> float:
        """
        Calculate skill level compatibility.
        
        Best matches:
        - Beginner + Intermediate/Advanced (if requester wants to learn)
        - Similar levels (for peer learning)
        """
        skill_order = {
            SkillLevel.BEGINNER: 1,
            SkillLevel.INTERMEDIATE: 2,
            SkillLevel.ADVANCED: 3,
            SkillLevel.EXPERT: 4
        }
        
        req_level = skill_order[requester_level]
        cand_level = skill_order[candidate_level]
        diff = abs(req_level - cand_level)
        
        # If requester wants to learn, prefer higher-skilled partners
        if preferred_role == SessionRole.LEARNER:
            if cand_level > req_level:
                return 1.0 - (diff - 1) * 0.2  # Prefer 1-2 levels higher
            else:
                return 0.3  # Lower skill not ideal for learning
        
        # If requester wants to tutor, prefer lower-skilled partners
        elif preferred_role == SessionRole.TUTOR:
            if cand_level < req_level:
                return 1.0 - (diff - 1) * 0.2
            else:
                return 0.3
        
        # For peer learning, prefer similar levels
        else:
            if diff == 0:
                return 1.0
            elif diff == 1:
                return 0.7
            else:
                return 0.4
    
    def _calculate_topic_overlap(
        self,
        requester: StudentProfile,
        candidate: StudentProfile,
        topic: str
    ) -> float:
        """
        Calculate topic overlap score.
        
        Best matches:
        - Candidate has mastered what requester is learning
        - Shared learning interests
        """
        score = 0.0
        
        # Check if topic is relevant
        if topic in candidate.topics_mastered and topic in requester.topics_learning:
            score += 0.5  # Perfect match - candidate can teach
        
        if topic in candidate.topics_learning and topic in requester.topics_learning:
            score += 0.3  # Good match - both learning
        
        # General topic overlap
        mastered_overlap = len(
            set(requester.topics_learning) & set(candidate.topics_mastered)
        )
        learning_overlap = len(
            set(requester.topics_learning) & set(candidate.topics_learning)
        )
        
        score += min(mastered_overlap * 0.1, 0.3)
        score += min(learning_overlap * 0.05, 0.2)
        
        return min(score, 1.0)
    
    def start_session(
        self,
        student1_id: str,
        student2_id: str,
        topic: str
    ) -> PeerSession:
        """
        Start a new peer learning session.
        
        Args:
            student1_id: First student
            student2_id: Second student (matched partner)
            topic: Topic for the session
            
        Returns:
            Created PeerSession
        """
        # Determine roles based on skill levels
        student1 = self.profiles.get(student1_id)
        student2 = self.profiles.get(student2_id)
        
        if not student1 or not student2:
            raise ValueError("Both students must have profiles")
        
        # Assign roles based on skill and topic mastery
        if topic in student1.topics_mastered and topic not in student2.topics_mastered:
            role1, role2 = SessionRole.TUTOR, SessionRole.LEARNER
        elif topic in student2.topics_mastered and topic not in student1.topics_mastered:
            role1, role2 = SessionRole.LEARNER, SessionRole.TUTOR
        else:
            role1, role2 = SessionRole.PEER, SessionRole.PEER
        
        session = PeerSession(
            session_id=str(uuid.uuid4()),
            student1_id=student1_id,
            student2_id=student2_id,
            topic=topic,
            student1_role=role1,
            student2_role=role2,
            status=SessionStatus.ACTIVE
        )
        
        self.sessions[session.session_id] = session
        
        # Update session counts
        student1.total_sessions += 1
        student2.total_sessions += 1
        
        return session

    def create_invite(
        self,
        requester_id: str,
        target_id: str,
        topic: str
    ) -> PeerSession:
        """
        Send a manual session invite to another student.
        """
        # Create session in PENDING state
        session = PeerSession(
            session_id=str(uuid.uuid4()),
            student1_id=requester_id,
            student2_id=target_id,
            topic=topic,
            student1_role=SessionRole.PEER, # Default to peer for manual
            student2_role=SessionRole.PEER,
            status=SessionStatus.PENDING,
            started_at=datetime.now()
        )
        self.sessions[session.session_id] = session
        return session

    def respond_to_invite(
        self,
        session_id: str,
        accept: bool
    ) -> Optional[PeerSession]:
        """
        Accept or reject a session invite.
        """
        session = self.sessions.get(session_id)
        if not session or session.status != SessionStatus.PENDING:
            return None
            
        if accept:
            session.status = SessionStatus.ACTIVE
            session.started_at = datetime.now() # Reset start time
            
            # Update stats
            s1 = self.profiles.get(session.student1_id)
            s2 = self.profiles.get(session.student2_id)
            if s1: s1.total_sessions += 1
            if s2: s2.total_sessions += 1
        else:
            session.status = SessionStatus.REJECTED
            session.ended_at = datetime.now()
            
        return session
    
    def get_session(self, session_id: str) -> Optional[PeerSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def end_session(
        self,
        session_id: str,
        student1_rating: Optional[float] = None,
        student2_rating: Optional[float] = None,
        notes: str = ""
    ) -> Optional[PeerSession]:
        """
        End a peer learning session.
        
        Args:
            session_id: Session to end
            student1_rating: Rating from student1 (1-5)
            student2_rating: Rating from student2 (1-5)
            notes: Session notes
            
        Returns:
            Updated session or None if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now()
        session.duration_minutes = int(
            (session.ended_at - session.started_at).total_seconds() / 60
        )
        session.student1_rating = student1_rating
        session.student2_rating = student2_rating
        session.notes = notes
        
        # Update average ratings
        if student1_rating:
            self._update_average_rating(session.student2_id, student1_rating)
        if student2_rating:
            self._update_average_rating(session.student1_id, student2_rating)
        
        return session
    
    def _update_average_rating(self, student_id: str, new_rating: float):
        """Update student's average rating"""
        profile = self.profiles.get(student_id)
        if not profile:
            return
        
        # Simple moving average
        total_sessions = profile.total_sessions
        if total_sessions == 0:
            profile.average_rating = new_rating
        else:
            profile.average_rating = (
                (profile.average_rating * (total_sessions - 1) + new_rating) / total_sessions
            )
    
    def get_student_sessions(
        self,
        student_id: str,
        status: Optional[SessionStatus] = None
    ) -> List[PeerSession]:
        """
        Get all sessions for a student.
        
        Args:
            student_id: Student ID
            status: Optional filter by status
            
        Returns:
            List of sessions
        """
        sessions = [
            s for s in self.sessions.values()
            if (s.student1_id == student_id or s.student2_id == student_id)
        ]
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # Sort by start time descending
        sessions.sort(key=lambda x: x.started_at, reverse=True)
        return sessions


# Singleton instance
peer_learning_service = PeerLearningService()
