"""
Teacher Analytics Service — Phase 4

Aggregates data from all three role backends to provide a live
classroom dashboard for the instructor:

  • Class Pulse       — average mastery, affect state, active students
  • At-Risk Students  — high frustration + low mastery
  • Student Profile   — per-student mastery breakdown + hint history
  • Chat Logs         — full tutoring conversation for a student
  • Mastery Heatmap   — concept × student mastery grid

Data sources (all in-process, no extra network calls):
  bkt_local       → LocalBKTEngine.get_student_summary() / get_mastery()
  affect_adapter  → AffectAdapter per-student profiles
  integration_bridge → hint_history dict (built during /submit calls)
  tutoring_engine → ConversationMemory (via HintGenerator._memory)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════
# Data models returned by the analytics API
# ═══════════════════════════════════════════════════════════════

@dataclass
class StudentRiskProfile:
    student_id: str
    overall_mastery: float          # 0-1
    frustration: float              # 0-1 latest reading
    engagement: float               # 0-1 latest reading
    total_hints_received: int
    weak_concepts: List[str]
    risk_level: str                 # "low" | "medium" | "high"
    risk_reason: str


@dataclass
class ConceptMasteryRow:
    student_id: str
    concept_masteries: Dict[str, float]   # concept → p(L)


@dataclass
class ClassPulse:
    timestamp: str
    active_students: int
    average_mastery: float
    average_frustration: float
    average_engagement: float
    at_risk_count: int
    most_struggled_concept: Optional[str]


# ═══════════════════════════════════════════════════════════════
# TeacherAnalytics
# ═══════════════════════════════════════════════════════════════

class TeacherAnalytics:
    """
    Central analytics engine for the teacher dashboard.

    Designed to be instantiated once (singleton) and queried by
    the teacher_routes API.  All heavy lifting is delegated to the
    existing singleton services to avoid data duplication.
    """

    # Thresholds for at-risk classification
    HIGH_FRUSTRATION = 0.65
    LOW_MASTERY      = 0.45
    MANY_HINTS       = 6     # hints in current session

    def __init__(self):
        # Lazy-import singletons to avoid circular imports at module load
        self._bkt_engine   = None   # LocalBKTEngine
        self._affect       = None   # AffectAdapter
        self._bridge       = None   # IntegrationBridge

    # ── Singleton accessors ───────────────────────────────────────

    def _get_bkt(self):
        if self._bkt_engine is None:
            from app.services.bkt_local import get_local_bkt
            self._bkt_engine = get_local_bkt()
        return self._bkt_engine

    def _get_affect(self):
        if self._affect is None:
            from app.services.affect_adapter import get_affect_adapter
            self._affect = get_affect_adapter()
        return self._affect

    def _get_bridge(self):
        if self._bridge is None:
            from app.services.integration_bridge import get_integration_bridge
            self._bridge = get_integration_bridge()
        return self._bridge

    # ── Internal helpers ──────────────────────────────────────────

    def _all_student_ids(self) -> List[str]:
        """Union of all known student IDs across all data sources."""
        ids = set()
        bkt = self._get_bkt()
        if hasattr(bkt, '_students'):
            ids.update(bkt._students.keys())
        affect = self._get_affect()
        if hasattr(affect, '_profiles'):
            ids.update(affect._profiles.keys())
        bridge = self._get_bridge()
        if hasattr(bridge, '_hint_history'):
            ids.update(bridge._hint_history.keys())
        return sorted(ids)

    def _student_mastery(self, student_id: str) -> float:
        """Average mastery across all concepts for a student (0-1)."""
        bkt = self._get_bkt()
        summary = bkt.get_student_summary(student_id)
        concepts: dict = summary.get("concept_mastery", {})
        if not concepts:
            return 0.0
        return sum(concepts.values()) / len(concepts)

    def _student_affect(self, student_id: str) -> Dict[str, float]:
        """Latest cognitive state for a student."""
        affect = self._get_affect()
        profiles = getattr(affect, '_profiles', {})
        profile = profiles.get(student_id)
        if profile is None:
            return {"frustration": 0.0, "engagement": 0.5, "confusion": 0.2, "boredom": 0.0}
        smoother = getattr(profile, 'smoother', None)
        if smoother is None:
            return {"frustration": 0.0, "engagement": 0.5, "confusion": 0.2, "boredom": 0.0}
        state = smoother.current()
        return {
            "frustration": getattr(state, 'frustration', 0.0),
            "engagement":  getattr(state, 'engagement', 0.5),
            "confusion":   getattr(state, 'confusion', 0.2),
            "boredom":     getattr(state, 'boredom', 0.0),
        }

    def _hint_count(self, student_id: str) -> int:
        bridge = self._get_bridge()
        history = getattr(bridge, '_hint_history', {})
        return len(history.get(student_id, []))

    def _weak_concepts(self, student_id: str, threshold: float = 0.5) -> List[str]:
        bkt = self._get_bkt()
        summary = bkt.get_student_summary(student_id)
        concepts: dict = summary.get("concept_mastery", {})
        return [c for c, m in concepts.items() if m < threshold]

    def _classify_risk(
        self, mastery: float, frustration: float, hint_count: int
    ) -> tuple[str, str]:
        reasons = []
        if mastery < self.LOW_MASTERY:
            reasons.append(f"low mastery ({mastery:.0%})")
        if frustration > self.HIGH_FRUSTRATION:
            reasons.append(f"high frustration ({frustration:.0%})")
        if hint_count >= self.MANY_HINTS:
            reasons.append(f"many hints ({hint_count})")

        if len(reasons) >= 2:
            return "high", "; ".join(reasons)
        if len(reasons) == 1:
            return "medium", reasons[0]
        return "low", "on track"

    # ── Public API ────────────────────────────────────────────────

    def get_class_pulse(self) -> ClassPulse:
        """Snapshot of the whole class right now."""
        student_ids = self._all_student_ids()
        if not student_ids:
            return ClassPulse(
                timestamp=datetime.now(timezone.utc).isoformat(),
                active_students=0,
                average_mastery=0.0,
                average_frustration=0.0,
                average_engagement=0.0,
                at_risk_count=0,
                most_struggled_concept=None,
            )

        masteries, frustrations, engagements = [], [], []
        at_risk = 0

        for sid in student_ids:
            m = self._student_mastery(sid)
            af = self._student_affect(sid)
            masteries.append(m)
            frustrations.append(af["frustration"])
            engagements.append(af["engagement"])
            level, _ = self._classify_risk(m, af["frustration"], self._hint_count(sid))
            if level in ("medium", "high"):
                at_risk += 1

        # Find concept most students are struggling with
        bkt = self._get_bkt()
        all_weak = []
        for sid in student_ids:
            all_weak.extend(self._weak_concepts(sid))

        from collections import Counter
        most_struggled = Counter(all_weak).most_common(1)
        struggled_concept = most_struggled[0][0] if most_struggled else None

        return ClassPulse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            active_students=len(student_ids),
            average_mastery=round(sum(masteries) / len(masteries), 3),
            average_frustration=round(sum(frustrations) / len(frustrations), 3),
            average_engagement=round(sum(engagements) / len(engagements), 3),
            at_risk_count=at_risk,
            most_struggled_concept=struggled_concept,
        )

    def get_at_risk_students(self) -> List[StudentRiskProfile]:
        """Return all students classified as medium or high risk."""
        at_risk = []
        for sid in self._all_student_ids():
            m = self._student_mastery(sid)
            af = self._student_affect(sid)
            hints = self._hint_count(sid)
            level, reason = self._classify_risk(m, af["frustration"], hints)
            if level in ("medium", "high"):
                at_risk.append(StudentRiskProfile(
                    student_id=sid,
                    overall_mastery=round(m, 3),
                    frustration=round(af["frustration"], 3),
                    engagement=round(af["engagement"], 3),
                    total_hints_received=hints,
                    weak_concepts=self._weak_concepts(sid),
                    risk_level=level,
                    risk_reason=reason,
                ))
        # Most at-risk first
        at_risk.sort(key=lambda r: (0 if r.risk_level == "high" else 1, -r.frustration))
        return at_risk

    def get_student_profile(self, student_id: str) -> Dict[str, Any]:
        """Full per-student breakdown for the teacher view."""
        bkt = self._get_bkt()
        summary = bkt.get_student_summary(student_id)
        af = self._student_affect(student_id)
        hints = self._hint_count(student_id)
        level, reason = self._classify_risk(
            self._student_mastery(student_id), af["frustration"], hints
        )
        return {
            "student_id": student_id,
            "risk_level": level,
            "risk_reason": reason,
            "bkt_summary": summary,
            "affect_state": af,
            "total_hints": hints,
            "weak_concepts": self._weak_concepts(student_id),
        }

    def get_chat_logs(self, student_id: str) -> List[Dict[str, Any]]:
        """Return the full hint / tutoring conversation for a student."""
        bridge = self._get_bridge()
        history = getattr(bridge, '_hint_history', {})
        return history.get(student_id, [])

    def get_mastery_heatmap(self) -> List[ConceptMasteryRow]:
        """
        Returns a grid: one row per student, columns are concepts.
        Teachers can visualise this as a colour-coded table.
        """
        rows = []
        bkt = self._get_bkt()
        for sid in self._all_student_ids():
            summary = bkt.get_student_summary(sid)
            concept_mastery: dict = summary.get("concept_mastery", {})
            rows.append(ConceptMasteryRow(
                student_id=sid,
                concept_masteries={c: round(m, 3) for c, m in concept_mastery.items()},
            ))
        return rows

    def get_all_students(self) -> List[str]:
        """List every known student ID."""
        return self._all_student_ids()


# ── Singleton ─────────────────────────────────────────────────

_analytics: Optional[TeacherAnalytics] = None


def get_teacher_analytics() -> TeacherAnalytics:
    global _analytics
    if _analytics is None:
        _analytics = TeacherAnalytics()
    return _analytics
