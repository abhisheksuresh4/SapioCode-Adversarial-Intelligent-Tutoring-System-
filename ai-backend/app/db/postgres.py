"""
PostgreSQL Models & Connection for SapioCode
Tables: users, submissions, viva_attempts, mastery_records, chat_logs, problems
"""
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Optional async support — only available with asyncpg
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker as async_sessionmaker
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://sapiocode:sapiocode@localhost:5432/sapiocode"
)
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://sapiocode:sapiocode@localhost:5432/sapiocode"
)

Base = declarative_base()

# Async engine (only created if asyncpg is available)
_async_engine = None
_async_session_factory = None

if ASYNC_AVAILABLE:
    try:
        _async_engine = create_async_engine(DATABASE_URL, echo=False)
        _async_session_factory = async_sessionmaker(
            _async_engine, class_=AsyncSession, expire_on_commit=False
        )
    except Exception:
        _async_engine = None
        _async_session_factory = None


# ─── User Model ───────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    submissions = relationship("Submission", back_populates="user")
    viva_attempts = relationship("VivaAttempt", back_populates="user")
    mastery_records = relationship("MasteryRecord", back_populates="user")
    chat_logs = relationship("ChatLog", back_populates="user")


# ─── Submission Model ─────────────────────────────────────────
class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(String(100), nullable=False, index=True)
    code = Column(Text, nullable=False)
    language = Column(String(20), default="python")

    execution_success = Column(Boolean, nullable=True)
    execution_output = Column(Text, nullable=True)
    execution_error = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)

    ast_complexity = Column(Integer, nullable=True)
    ast_pattern = Column(String(50), nullable=True)
    ast_issues = Column(JSON, nullable=True)
    concepts_detected = Column(JSON, nullable=True)

    mastery_before = Column(Float, nullable=True)
    mastery_after = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    hint_count = Column(Integer, default=0)
    frustration_score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")


# ─── Viva Attempt Model ───────────────────────────────────────
class VivaAttempt(Base):
    __tablename__ = "viva_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    problem_id = Column(String(100), nullable=False)

    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)
    transcript = Column(Text, nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)

    verdict = Column(String(20), nullable=True)
    confidence_score = Column(Float, nullable=True)
    concept_overlap_score = Column(Float, nullable=True)
    matched_concepts = Column(JSON, nullable=True)
    missed_concepts = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)

    attempted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="viva_attempts")


# ─── Mastery / BKT Model ─────────────────────────────────────
class MasteryRecord(Base):
    __tablename__ = "mastery_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    concept = Column(String(100), nullable=False, index=True)

    p_mastery = Column(Float, default=0.1)
    p_learn = Column(Float, default=0.2)
    p_guess = Column(Float, default=0.25)
    p_slip = Column(Float, default=0.1)
    p_transit = Column(Float, default=0.1)

    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    streak = Column(Integer, default=0)

    last_updated = Column(DateTime, default=datetime.utcnow)
    is_mastered = Column(Boolean, default=False)

    user = relationship("User", back_populates="mastery_records")


# ─── Chat / Hint Log Model ────────────────────────────────────
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=True)

    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    hint_level = Column(Integer, nullable=True)

    frustration_at_time = Column(Float, nullable=True)
    mastery_at_time = Column(Float, nullable=True)
    intervention_type = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_logs")


# ─── Problem Bank Model ──────────────────────────────────────
class Problem(Base):
    __tablename__ = "problems"

    id = Column(String(100), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(20), nullable=False)
    concepts = Column(JSON, nullable=False)
    starter_code = Column(Text, nullable=True)
    solution_template = Column(Text, nullable=True)
    test_cases = Column(JSON, nullable=True)
    hints = Column(JSON, nullable=True)
    time_limit_seconds = Column(Integer, default=30)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    graph_node_id = Column(String(100), nullable=True)
    prerequisites = Column(JSON, nullable=True)


# ─── Database Initialization ──────────────────────────────────
async def init_db():
    """Create all tables (requires asyncpg)"""
    if _async_engine is None:
        raise RuntimeError("Async DB engine not available. Install asyncpg.")
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency for async DB sessions"""
    if _async_session_factory is None:
        raise RuntimeError("Async DB sessions not available. Install asyncpg.")
    async with _async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
