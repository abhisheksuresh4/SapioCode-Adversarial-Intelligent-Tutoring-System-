"""
Session Persistence Store — SQLite Backend

Persists tutoring sessions, hint history, viva attempts, and conversation
turns so data survives server restarts.

Tables:
  sessions        — one row per student + problem combo
  hint_history    — every hint ever given
  viva_attempts   — every viva voce attempt + verdict
  conversations   — full conversation memory per student
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


# ═══════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class SessionRecord:
    """A tutoring session for a specific student + problem."""
    session_id: str
    student_id: str
    problem_description: str
    created_at: str = ""
    last_active: str = ""
    total_hints: int = 0
    total_submissions: int = 0
    best_mastery: float = 0.0
    status: str = "active"  # active | completed | abandoned


@dataclass
class HintRecord:
    """A single hint given to a student."""
    student_id: str
    session_id: str
    hint_text: str
    hint_level: int
    hint_path: str  # gentle | socratic | challenge
    teaching_focus: str
    timestamp: str = ""
    frustration_at_time: float = 0.0
    mastery_at_time: float = 0.0


@dataclass
class VivaAttemptRecord:
    """A single Viva Voce attempt."""
    student_id: str
    session_id: str
    question: str
    transcribed_answer: str
    verdict: str  # PASS | FAIL | PARTIAL
    score: float
    concept_overlap_score: float = 0.0
    timestamp: str = ""


@dataclass
class ConversationRecord:
    """A single turn in a tutoring conversation."""
    student_id: str
    role: str  # student | tutor
    content: str
    hint_level: int = 0
    teaching_focus: str = ""
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════
# SESSION STORE
# ═══════════════════════════════════════════════════════════

class SessionStore:
    """SQLite-backed session persistence for SapioCode tutoring."""

    def __init__(self, db_path: str = "sapiocode_sessions.db"):
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._init_schema()

    @property
    def _conn(self) -> sqlite3.Connection:
        """Thread-local connection (SQLite is not thread-safe)."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id    TEXT PRIMARY KEY,
                student_id    TEXT NOT NULL,
                problem_description TEXT,
                created_at    TEXT NOT NULL,
                last_active   TEXT NOT NULL,
                total_hints   INTEGER DEFAULT 0,
                total_submissions INTEGER DEFAULT 0,
                best_mastery  REAL DEFAULT 0.0,
                status        TEXT DEFAULT 'active'
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_student
                ON sessions(student_id);

            CREATE TABLE IF NOT EXISTS hint_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    TEXT NOT NULL,
                session_id    TEXT NOT NULL,
                hint_text     TEXT NOT NULL,
                hint_level    INTEGER,
                hint_path     TEXT,
                teaching_focus TEXT,
                timestamp     TEXT NOT NULL,
                frustration_at_time REAL DEFAULT 0.0,
                mastery_at_time REAL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_hints_student
                ON hint_history(student_id);

            CREATE TABLE IF NOT EXISTS viva_attempts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    TEXT NOT NULL,
                session_id    TEXT NOT NULL,
                question      TEXT,
                transcribed_answer TEXT,
                verdict       TEXT,
                score         REAL,
                concept_overlap_score REAL DEFAULT 0.0,
                timestamp     TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_viva_student
                ON viva_attempts(student_id);

            CREATE TABLE IF NOT EXISTS conversations (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    TEXT NOT NULL,
                role          TEXT NOT NULL,
                content       TEXT NOT NULL,
                hint_level    INTEGER DEFAULT 0,
                teaching_focus TEXT DEFAULT '',
                timestamp     TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conv_student
                ON conversations(student_id);
        """)
        conn.commit()

    # ── SESSION CRUD ────────────────────────────────────

    def create_session(
        self,
        session_id: str,
        student_id: str,
        problem_description: str,
    ) -> SessionRecord:
        """Create a new tutoring session."""
        now = datetime.now(timezone.utc).isoformat()
        record = SessionRecord(
            session_id=session_id,
            student_id=student_id,
            problem_description=problem_description,
            created_at=now,
            last_active=now,
        )
        self._conn.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, student_id, problem_description, created_at,
                last_active, total_hints, total_submissions, best_mastery, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.session_id, record.student_id, record.problem_description,
                record.created_at, record.last_active, record.total_hints,
                record.total_submissions, record.best_mastery, record.status,
            ),
        )
        self._conn.commit()
        return record

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Retrieve a session by ID."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return SessionRecord(**dict(row))

    def get_student_sessions(self, student_id: str) -> List[SessionRecord]:
        """Get all sessions for a student, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE student_id = ? ORDER BY last_active DESC",
            (student_id,),
        ).fetchall()
        return [SessionRecord(**dict(r)) for r in rows]

    def update_session_activity(
        self, session_id: str, hints_delta: int = 0,
        submissions_delta: int = 0, mastery: float | None = None,
    ) -> None:
        """Bump last_active and increment counters."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """UPDATE sessions SET
                 last_active = ?,
                 total_hints = total_hints + ?,
                 total_submissions = total_submissions + ?,
                 best_mastery = COALESCE(MAX(best_mastery, ?), best_mastery)
               WHERE session_id = ?""",
            (now, hints_delta, submissions_delta, mastery, session_id),
        )
        self._conn.commit()

    def complete_session(self, session_id: str) -> None:
        """Mark a session as completed."""
        self._conn.execute(
            "UPDATE sessions SET status = 'completed' WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()

    # ── HINT HISTORY ────────────────────────────────────

    def record_hint(self, hint: HintRecord) -> None:
        """Store a hint that was given."""
        if not hint.timestamp:
            hint.timestamp = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO hint_history
               (student_id, session_id, hint_text, hint_level, hint_path,
                teaching_focus, timestamp, frustration_at_time, mastery_at_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                hint.student_id, hint.session_id, hint.hint_text,
                hint.hint_level, hint.hint_path, hint.teaching_focus,
                hint.timestamp, hint.frustration_at_time, hint.mastery_at_time,
            ),
        )
        self._conn.commit()

    def get_hint_history(
        self, student_id: str, session_id: Optional[str] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve hint history, optionally filtered by session."""
        if session_id:
            rows = self._conn.execute(
                """SELECT * FROM hint_history
                   WHERE student_id = ? AND session_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (student_id, session_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM hint_history
                   WHERE student_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (student_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── VIVA ATTEMPTS ───────────────────────────────────

    def record_viva_attempt(self, attempt: VivaAttemptRecord) -> None:
        """Store a Viva Voce attempt."""
        if not attempt.timestamp:
            attempt.timestamp = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO viva_attempts
               (student_id, session_id, question, transcribed_answer,
                verdict, score, concept_overlap_score, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attempt.student_id, attempt.session_id, attempt.question,
                attempt.transcribed_answer, attempt.verdict, attempt.score,
                attempt.concept_overlap_score, attempt.timestamp,
            ),
        )
        self._conn.commit()

    def get_viva_attempts(
        self, student_id: str, limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve viva attempts for a student."""
        rows = self._conn.execute(
            """SELECT * FROM viva_attempts
               WHERE student_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (student_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── CONVERSATION MEMORY ─────────────────────────────

    def record_conversation_turn(self, turn: ConversationRecord) -> None:
        """Store a conversation turn."""
        if not turn.timestamp:
            turn.timestamp = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO conversations
               (student_id, role, content, hint_level, teaching_focus, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                turn.student_id, turn.role, turn.content,
                turn.hint_level, turn.teaching_focus, turn.timestamp,
            ),
        )
        self._conn.commit()

    def get_conversation(
        self, student_id: str, limit: int = 20,
    ) -> List[Dict[str, str]]:
        """Retrieve recent conversation turns as OpenAI-format messages."""
        rows = self._conn.execute(
            """SELECT role, content FROM conversations
               WHERE student_id = ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (student_id, limit),
        ).fetchall()
        return [
            {"role": r["role"] if r["role"] != "tutor" else "assistant",
             "content": r["content"]}
            for r in rows
        ]

    def clear_conversation(self, student_id: str) -> int:
        """Clear conversation for a student. Returns rows deleted."""
        cursor = self._conn.execute(
            "DELETE FROM conversations WHERE student_id = ?",
            (student_id,),
        )
        self._conn.commit()
        return cursor.rowcount

    # ── ANALYTICS QUERIES ───────────────────────────────

    def get_student_stats(self, student_id: str) -> Dict[str, Any]:
        """Aggregate stats for a student across all sessions."""
        session_count = self._conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE student_id = ?",
            (student_id,),
        ).fetchone()[0]

        total_hints = self._conn.execute(
            "SELECT COUNT(*) FROM hint_history WHERE student_id = ?",
            (student_id,),
        ).fetchone()[0]

        viva_count = self._conn.execute(
            "SELECT COUNT(*) FROM viva_attempts WHERE student_id = ?",
            (student_id,),
        ).fetchone()[0]

        viva_pass_rate = 0.0
        if viva_count > 0:
            passes = self._conn.execute(
                "SELECT COUNT(*) FROM viva_attempts WHERE student_id = ? AND verdict = 'PASS'",
                (student_id,),
            ).fetchone()[0]
            viva_pass_rate = passes / viva_count

        return {
            "student_id": student_id,
            "total_sessions": session_count,
            "total_hints": total_hints,
            "total_viva_attempts": viva_count,
            "viva_pass_rate": round(viva_pass_rate, 2),
        }

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ═══════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════

_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get or create the session store singleton."""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
