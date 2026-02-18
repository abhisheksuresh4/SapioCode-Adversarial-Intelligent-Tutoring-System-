"""
Local BKT (Bayesian Knowledge Tracing) Engine for SapioCode

This is a direct port of Role 3's BKT math (SapioCode/bkt/model.py,
affect_fusion.py, explainability.py) running LOCALLY inside Role 2.

Purpose:
  - Fallback when Role 3's Neo4j/BKT service is offline
  - Enables Role 2 to make mastery-aware tutoring decisions WITHOUT
    requiring an HTTP call to Role 3 for every single hint
  - Uses the EXACT same formulas as Role 3 for consistency

Ported from:
  SapioCode/bkt/model.py       → bkt_update()
  SapioCode/bkt/affect_fusion.py → modulate_bkt_params()
  SapioCode/bkt/explainability.py → explain_bkt_update()
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.core.config import get_settings


# ═══════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════

@dataclass
class BKTParams:
    """BKT parameters for a concept"""
    p_T: float = 0.1    # Probability of learning (transition)
    p_S: float = 0.1    # Probability of slip (knows but wrong)
    p_G: float = 0.2    # Probability of guess (doesn't know but right)


@dataclass
class CognitiveState:
    """
    Student's real-time cognitive/emotional state.
    Comes from Role 3's Face-API.js → affectToCognition.js → cognitiveSmoother.js

    Role 3's exact mapping (affectToCognition.js):
      engagement  = happy*0.6 + surprised*0.4
      confusion   = surprised*0.6 + sad*0.4
      frustration = angry*0.5 + fearful*0.3 + sad*0.2
      boredom     = neutral*0.8 - (happy+surprised)*0.4
    """
    engagement: float = 0.7
    frustration: float = 0.1
    confusion: float = 0.2
    boredom: float = 0.0


@dataclass
class MasteryRecord:
    """Mastery state for a single concept"""
    concept: str
    mastery: float             # p(L) — probability of knowing
    attempts: int = 0
    correct_count: int = 0
    last_params: Optional[BKTParams] = None


@dataclass
class BKTUpdateResult:
    """Complete result of a BKT update"""
    concept: str
    old_mastery: float
    new_mastery: float
    mastery_delta: float
    base_params: Dict[str, float]
    adapted_params: Dict[str, float]
    is_mastered: bool
    explanation: Dict[str, Any]


# ═══════════════════════════════════════════════
# Core BKT Math — exact port of Role 3's model.py
# ═══════════════════════════════════════════════

def bkt_update(
    p_L: float,
    correct: bool,
    p_T: float = 0.1,
    p_S: float = 0.1,
    p_G: float = 0.2
) -> float:
    """
    Perform one Bayesian Knowledge Tracing update.

    Exact replica of SapioCode/bkt/model.py

    Args:
        p_L:  Prior mastery probability
        correct: True if student answered correctly
        p_T:  Probability of learning
        p_S:  Slip probability (knows but gets it wrong)
        p_G:  Guess probability (doesn't know but gets it right)

    Returns:
        Updated mastery probability (clamped to [0, 1])
    """
    # Bayesian posterior update
    if correct:
        numerator = p_L * (1 - p_S)
        denominator = numerator + (1 - p_L) * p_G
    else:
        numerator = p_L * p_S
        denominator = numerator + (1 - p_L) * (1 - p_G)

    if denominator == 0:
        posterior = p_L
    else:
        posterior = numerator / denominator

    # Learning transition
    updated_p_L = posterior + (1 - posterior) * p_T

    # Numerical safety
    return min(max(updated_p_L, 0.0), 1.0)


# ═══════════════════════════════════════════════
# Affect Fusion — exact port of Role 3's affect_fusion.py
# ═══════════════════════════════════════════════

def modulate_bkt_params(
    base_params: BKTParams,
    cognitive_state: CognitiveState
) -> BKTParams:
    """
    Adjust BKT parameters using the student's affective state.

    Exact replica of SapioCode/bkt/affect_fusion.py

    Modulation rules (from Role 3):
      - High engagement  → learn rate INCREASES  (+50%)
      - High frustration → learn rate DECREASES  (-60%)
      - High confusion   → slip rate INCREASES   (+70%)
      - High boredom     → guess rate INCREASES  (+50%)
      - High boredom     → learn rate DECREASES  (-40%)
    """
    learn = base_params.p_T
    slip = base_params.p_S
    guess = base_params.p_G

    # Apply modulation — EXACT multipliers from Role 3
    learn *= (1 + cognitive_state.engagement * 0.5)
    learn *= (1 - cognitive_state.frustration * 0.6)
    slip *= (1 + cognitive_state.confusion * 0.7)
    guess *= (1 + cognitive_state.boredom * 0.5)
    learn *= (1 - cognitive_state.boredom * 0.4)

    # Clamp probabilities to valid range
    learn = min(max(learn, 0.01), 0.9)
    slip = min(max(slip, 0.01), 0.9)
    guess = min(max(guess, 0.01), 0.9)

    return BKTParams(p_T=learn, p_S=slip, p_G=guess)


# ═══════════════════════════════════════════════
# Explainability — exact port of Role 3's explainability.py
# ═══════════════════════════════════════════════

def explain_bkt_update(
    cognitive_state: CognitiveState,
    base_params: BKTParams,
    adapted_params: BKTParams,
    old_mastery: float,
    new_mastery: float
) -> Dict[str, Any]:
    """
    Generate human-readable explanation for a mastery update.

    Exact replica of SapioCode/bkt/explainability.py
    """
    explanations: List[str] = []

    # Affect-based reasoning
    if cognitive_state.frustration > 0.5:
        explanations.append(
            "Learning rate was reduced due to high frustration."
        )
    if cognitive_state.engagement > 0.5:
        explanations.append(
            "Learning rate was increased due to strong engagement."
        )
    if cognitive_state.confusion > 0.4:
        explanations.append(
            "Error probability increased due to observed confusion."
        )
    if cognitive_state.boredom > 0.5:
        explanations.append(
            "Guessing likelihood increased due to signs of boredom."
        )

    # Mastery outcome
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
            "cognitive_state": {
                "engagement": cognitive_state.engagement,
                "frustration": cognitive_state.frustration,
                "confusion": cognitive_state.confusion,
                "boredom": cognitive_state.boredom,
            },
            "base_params": {
                "p_T": base_params.p_T,
                "p_S": base_params.p_S,
                "p_G": base_params.p_G,
            },
            "adapted_params": {
                "p_T": adapted_params.p_T,
                "p_S": adapted_params.p_S,
                "p_G": adapted_params.p_G,
            },
            "mastery_change": round(delta, 4),
        },
    }


# ═══════════════════════════════════════════════
# Local BKT Engine — manages per-student mastery in-memory
# ═══════════════════════════════════════════════

class LocalBKTEngine:
    """
    In-memory BKT engine that tracks student mastery per concept.

    This runs inside Role 2 as a LOCAL fallback when Role 3's
    Neo4j-backed BKT service is unavailable. It uses the exact
    same math as Role 3 for consistency.

    In production, this also serves as a fast cache — we compute
    mastery locally for immediate tutoring decisions, then async
    sync with Role 3's Neo4j for persistence.
    """

    def __init__(self):
        settings = get_settings()
        self.default_params = BKTParams(
            p_T=settings.BKT_DEFAULT_P_T,
            p_S=settings.BKT_DEFAULT_P_S,
            p_G=settings.BKT_DEFAULT_P_G,
        )
        self.mastery_threshold = settings.MASTERY_THRESHOLD

        # In-memory store: {student_id: {concept: MasteryRecord}}
        self._store: Dict[str, Dict[str, MasteryRecord]] = {}

    def get_mastery(self, student_id: str, concept: str) -> float:
        """Get current mastery for a student-concept pair"""
        settings = get_settings()
        student = self._store.get(student_id, {})
        record = student.get(concept)
        return record.mastery if record else settings.BKT_DEFAULT_P_L

    def get_all_mastery(self, student_id: str) -> Dict[str, float]:
        """Get all concept masteries for a student"""
        student = self._store.get(student_id, {})
        return {concept: rec.mastery for concept, rec in student.items()}

    def is_mastered(self, student_id: str, concept: str) -> bool:
        """Check if a concept is considered mastered"""
        return self.get_mastery(student_id, concept) >= self.mastery_threshold

    def update_mastery(
        self,
        student_id: str,
        concept: str,
        correct: bool,
        cognitive_state: Optional[CognitiveState] = None,
        custom_params: Optional[BKTParams] = None,
    ) -> BKTUpdateResult:
        """
        Run one BKT update for a student-concept pair.

        Args:
            student_id: Student identifier
            concept: Concept name (e.g. "recursion", "linked_lists")
            correct: Whether the attempt was correct
            cognitive_state: Emotional state for affect fusion
            custom_params: Override default BKT params (from Neo4j)

        Returns:
            BKTUpdateResult with old/new mastery + explanation
        """
        # Get or create mastery record
        if student_id not in self._store:
            self._store[student_id] = {}

        student = self._store[student_id]
        if concept not in student:
            settings = get_settings()
            student[concept] = MasteryRecord(
                concept=concept,
                mastery=settings.BKT_DEFAULT_P_L,
            )

        record = student[concept]
        old_mastery = record.mastery
        base_params = custom_params or self.default_params

        # Step 1: Modulate BKT params with affect (if available)
        if cognitive_state:
            adapted_params = modulate_bkt_params(base_params, cognitive_state)
        else:
            adapted_params = base_params

        # Step 2: Run BKT update
        new_mastery = bkt_update(
            p_L=old_mastery,
            correct=correct,
            p_T=adapted_params.p_T,
            p_S=adapted_params.p_S,
            p_G=adapted_params.p_G,
        )

        # Step 3: Generate explanation
        cog = cognitive_state or CognitiveState()
        explanation = explain_bkt_update(
            cognitive_state=cog,
            base_params=base_params,
            adapted_params=adapted_params,
            old_mastery=old_mastery,
            new_mastery=new_mastery,
        )

        # Step 4: Update record
        record.mastery = new_mastery
        record.attempts += 1
        if correct:
            record.correct_count += 1
        record.last_params = adapted_params

        return BKTUpdateResult(
            concept=concept,
            old_mastery=round(old_mastery, 4),
            new_mastery=round(new_mastery, 4),
            mastery_delta=round(new_mastery - old_mastery, 4),
            base_params={
                "p_T": base_params.p_T,
                "p_S": base_params.p_S,
                "p_G": base_params.p_G,
            },
            adapted_params={
                "p_T": round(adapted_params.p_T, 4),
                "p_S": round(adapted_params.p_S, 4),
                "p_G": round(adapted_params.p_G, 4),
            },
            is_mastered=new_mastery >= self.mastery_threshold,
            explanation=explanation,
        )

    def bulk_update(
        self,
        student_id: str,
        concepts: List[str],
        correct: bool,
        cognitive_state: Optional[CognitiveState] = None,
    ) -> List[BKTUpdateResult]:
        """
        Update mastery for multiple concepts at once.
        Used when a problem tests multiple concepts.
        """
        return [
            self.update_mastery(student_id, concept, correct, cognitive_state)
            for concept in concepts
        ]

    def get_weakest_concepts(
        self, student_id: str, top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """Get the N concepts with lowest mastery for a student"""
        student = self._store.get(student_id, {})
        if not student:
            return []

        sorted_concepts = sorted(
            student.values(), key=lambda r: r.mastery
        )

        return [
            {
                "concept": rec.concept,
                "mastery": round(rec.mastery, 4),
                "attempts": rec.attempts,
                "is_mastered": rec.mastery >= self.mastery_threshold,
            }
            for rec in sorted_concepts[:top_n]
        ]

    def get_student_summary(self, student_id: str) -> Dict[str, Any]:
        """Get a full summary of a student's mastery state"""
        student = self._store.get(student_id, {})
        if not student:
            return {
                "student_id": student_id,
                "total_concepts": 0,
                "mastered_count": 0,
                "average_mastery": 0.0,
                "concepts": {},
            }

        masteries = {c: round(r.mastery, 4) for c, r in student.items()}
        mastered = sum(1 for r in student.values() if r.mastery >= self.mastery_threshold)

        return {
            "student_id": student_id,
            "total_concepts": len(student),
            "mastered_count": mastered,
            "average_mastery": round(
                sum(r.mastery for r in student.values()) / len(student), 4
            ),
            "weakest": self.get_weakest_concepts(student_id),
            "concepts": masteries,
        }


# ═══════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════

_bkt_engine: Optional[LocalBKTEngine] = None


def get_bkt_engine() -> LocalBKTEngine:
    """Get or create the local BKT engine singleton"""
    global _bkt_engine
    if _bkt_engine is None:
        _bkt_engine = LocalBKTEngine()
    return _bkt_engine
