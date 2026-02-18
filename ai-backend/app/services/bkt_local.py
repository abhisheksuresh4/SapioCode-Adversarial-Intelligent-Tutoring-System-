"""
Local BKT Engine — Exact port of Role 3's Bayesian Knowledge Tracing math.

This module replicates the BKT algorithm from:
  SapioCode/bkt/model.py        → bkt_update()
  SapioCode/bkt/affect_fusion.py → modulate_bkt_params()
  SapioCode/bkt/explainability.py → explain_bkt_update()

PURPOSE:
  When Role 3's Neo4j server is offline, we still need to compute mastery
  locally so the tutoring engine can make hint-level decisions.
  When Role 3 IS online, we call their /submit endpoint AND run local
  BKT so we have the mastery value immediately (no extra round-trip).

The math is IDENTICAL to Role 3's implementation.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════
# Core BKT Algorithm  (mirrors SapioCode/bkt/model.py)
# ═══════════════════════════════════════════════════

def bkt_update(
    p_L: float,
    correct: bool,
    p_T: float = 0.1,
    p_S: float = 0.1,
    p_G: float = 0.2
) -> float:
    """
    One Bayesian Knowledge Tracing update step.

    p_L : prior mastery probability  (0.0 – 1.0)
    correct : True if student answered correctly
    p_T : probability of learning (transition)
    p_S : slip probability (knows but answers wrong)
    p_G : guess probability (doesn't know but answers right)

    Returns: updated mastery probability
    """
    # — Bayesian posterior update —
    if correct:
        numerator = p_L * (1 - p_S)
        denominator = numerator + (1 - p_L) * p_G
    else:
        numerator = p_L * p_S
        denominator = numerator + (1 - p_L) * (1 - p_G)

    posterior = p_L if denominator == 0 else (numerator / denominator)

    # — Learning transition —
    updated_p_L = posterior + (1 - posterior) * p_T

    # — Numerical safety —
    return min(max(updated_p_L, 0.0), 1.0)


# ═══════════════════════════════════════════════════
# Affect Fusion  (mirrors SapioCode/bkt/affect_fusion.py)
# ═══════════════════════════════════════════════════

def modulate_bkt_params(base_params: dict, cognitive_state: dict) -> dict:
    """
    Adjust BKT parameters using the student's affective state.

    Exact multipliers from Role 3:
      engagement  → boosts   learn  by up to +50 %
      frustration → reduces  learn  by up to −60 %
      confusion   → increases slip   by up to +70 %
      boredom     → increases guess  by up to +50 %
      boredom     → also reduces learn by up to −40 %
    """
    learn = base_params["p_T"]
    slip  = base_params["p_S"]
    guess = base_params["p_G"]

    engagement  = cognitive_state.get("engagement", 0.0)
    frustration = cognitive_state.get("frustration", 0.0)
    confusion   = cognitive_state.get("confusion", 0.0)
    boredom     = cognitive_state.get("boredom", 0.0)

    # — Apply modulation (identical to Role 3) —
    learn *= (1 + engagement * 0.5)
    learn *= (1 - frustration * 0.6)
    slip  *= (1 + confusion * 0.7)
    guess *= (1 + boredom * 0.5)
    learn *= (1 - boredom * 0.4)

    # — Clamp probabilities —
    learn = min(max(learn, 0.01), 0.9)
    slip  = min(max(slip,  0.01), 0.9)
    guess = min(max(guess, 0.01), 0.9)

    return {"p_T": learn, "p_S": slip, "p_G": guess}


# ═══════════════════════════════════════════════════
# Explainability  (mirrors SapioCode/bkt/explainability.py)
# ═══════════════════════════════════════════════════

def explain_bkt_update(
    cognitive_state: dict,
    base_params: dict,
    adapted_params: dict,
    old_mastery: float,
    new_mastery: float
) -> dict:
    """
    Generate human-readable explanation for a mastery update.
    Used by the teacher dashboard and tutoring engine.
    """
    explanations: List[str] = []

    if cognitive_state.get("frustration", 0) > 0.5:
        explanations.append("Learning rate was reduced due to high frustration.")
    if cognitive_state.get("engagement", 0) > 0.5:
        explanations.append("Learning rate was increased due to strong engagement.")
    if cognitive_state.get("confusion", 0) > 0.4:
        explanations.append("Error probability increased due to observed confusion.")
    if cognitive_state.get("boredom", 0) > 0.5:
        explanations.append("Guessing likelihood increased due to signs of boredom.")

    delta = new_mastery - old_mastery
    if delta > 0.05:
        explanations.append("Student mastery improved significantly.")
    elif delta > 0:
        explanations.append("Student mastery improved gradually.")
    else:
        explanations.append("No mastery improvement observed in this attempt.")

    return {
        "summary": " ".join(explanations),
        "details": {
            "cognitive_state": cognitive_state,
            "base_params": base_params,
            "adapted_params": adapted_params,
            "mastery_change": round(delta, 4)
        }
    }


# ═══════════════════════════════════════════════════
# Student Mastery Store  (in-memory, replaces Neo4j)
# ═══════════════════════════════════════════════════

# Default BKT parameters per concept (same defaults as Role 3's Neo4j nodes)
DEFAULT_BKT_PARAMS = {
    "p_T": 0.1,   # learning rate
    "p_S": 0.1,   # slip probability
    "p_G": 0.2,   # guess probability
}

INITIAL_MASTERY = 0.3  # Start assumption: 30% mastery


@dataclass
class ConceptMastery:
    """Mastery state for one student-concept pair"""
    concept: str
    mastery: float = INITIAL_MASTERY
    bkt_params: dict = field(default_factory=lambda: dict(DEFAULT_BKT_PARAMS))
    attempts: int = 0
    correct_count: int = 0
    last_explanation: str = ""


@dataclass
class StudentRecord:
    """Complete mastery record for a student"""
    student_id: str
    concepts: Dict[str, ConceptMastery] = field(default_factory=dict)
    submission_history: List[dict] = field(default_factory=list)


class LocalBKTEngine:
    """
    In-memory BKT engine that mirrors Role 3's Neo4j-backed pipeline.

    Use this:
    - As a FALLBACK when Neo4j / Role 3 is offline
    - For IMMEDIATE mastery reads without a network round-trip
    - For the tutoring engine to query mastery mid-session
    """

    def __init__(self):
        self._students: Dict[str, StudentRecord] = {}

    # ── Get or create student ──────────────────────
    def _get_student(self, student_id: str) -> StudentRecord:
        if student_id not in self._students:
            self._students[student_id] = StudentRecord(student_id=student_id)
        return self._students[student_id]

    def _get_concept(self, student_id: str, concept: str) -> ConceptMastery:
        student = self._get_student(student_id)
        if concept not in student.concepts:
            student.concepts[concept] = ConceptMastery(concept=concept)
        return student.concepts[concept]

    # ── Main update pipeline ──────────────────────
    def process_submission(
        self,
        student_id: str,
        concepts: List[str],
        correct: bool,
        cognitive_state: Optional[dict] = None
    ) -> Dict[str, dict]:
        """
        Run the full BKT pipeline for a submission.

        Args:
            student_id: Student identifier
            concepts: List of concepts this problem tests
            correct: Whether the submission passed
            cognitive_state: Affect data {frustration, engagement, confusion, boredom}

        Returns:
            Dict of concept → {old_mastery, new_mastery, explanation}
        """
        if cognitive_state is None:
            cognitive_state = {
                "engagement": 0.7,
                "frustration": 0.1,
                "confusion": 0.2,
                "boredom": 0.0
            }

        results = {}

        for concept_name in concepts:
            cm = self._get_concept(student_id, concept_name)
            old_mastery = cm.mastery

            # 1. Modulate BKT params with affect
            adapted_params = modulate_bkt_params(cm.bkt_params, cognitive_state)

            # 2. Run BKT update
            new_mastery = bkt_update(
                p_L=old_mastery,
                correct=correct,
                p_T=adapted_params["p_T"],
                p_S=adapted_params["p_S"],
                p_G=adapted_params["p_G"]
            )

            # 3. Generate explanation
            explanation = explain_bkt_update(
                cognitive_state=cognitive_state,
                base_params=cm.bkt_params,
                adapted_params=adapted_params,
                old_mastery=old_mastery,
                new_mastery=new_mastery
            )

            # 4. Persist locally
            cm.mastery = new_mastery
            cm.attempts += 1
            if correct:
                cm.correct_count += 1
            cm.last_explanation = explanation["summary"]

            results[concept_name] = {
                "old_mastery": round(old_mastery, 4),
                "new_mastery": round(new_mastery, 4),
                "delta": round(new_mastery - old_mastery, 4),
                "adapted_params": adapted_params,
                "explanation": explanation
            }

        # Record in history
        student = self._get_student(student_id)
        student.submission_history.append({
            "concepts": concepts,
            "correct": correct,
            "cognitive_state": cognitive_state,
            "results": {k: v["new_mastery"] for k, v in results.items()}
        })

        return results

    # ── Query helpers ──────────────────────────────
    def get_mastery(self, student_id: str, concept: str) -> float:
        """Get current mastery probability for a concept"""
        cm = self._get_concept(student_id, concept)
        return cm.mastery

    def get_all_mastery(self, student_id: str) -> Dict[str, float]:
        """Get mastery for all concepts a student has attempted"""
        student = self._get_student(student_id)
        return {c: cm.mastery for c, cm in student.concepts.items()}

    def get_weakest_concepts(self, student_id: str, n: int = 3) -> List[str]:
        """Get the N weakest concepts for a student (for remediation)"""
        all_mastery = self.get_all_mastery(student_id)
        if not all_mastery:
            return []
        sorted_concepts = sorted(all_mastery.items(), key=lambda x: x[1])
        return [c for c, _ in sorted_concepts[:n]]

    def get_student_summary(self, student_id: str) -> dict:
        """Full summary for teacher dashboard"""
        student = self._get_student(student_id)
        masteries = self.get_all_mastery(student_id)
        avg_mastery = sum(masteries.values()) / max(len(masteries), 1)

        return {
            "student_id": student_id,
            "concepts_attempted": len(student.concepts),
            "total_submissions": len(student.submission_history),
            "average_mastery": round(avg_mastery, 4),
            "mastery_by_concept": {k: round(v, 4) for k, v in masteries.items()},
            "weakest_concepts": self.get_weakest_concepts(student_id),
            "submission_count": sum(
                cm.attempts for cm in student.concepts.values()
            )
        }


# ── Singleton ──────────────────────────────────
_bkt_engine: Optional[LocalBKTEngine] = None


def get_local_bkt() -> LocalBKTEngine:
    global _bkt_engine
    if _bkt_engine is None:
        _bkt_engine = LocalBKTEngine()
    return _bkt_engine
