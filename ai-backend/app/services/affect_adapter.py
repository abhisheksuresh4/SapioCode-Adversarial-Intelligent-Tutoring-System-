"""
Affect Adapter — Server-side port of Role 3's frontend emotion processing.

Mirrors the logic from:
  SapioCode/cognitcode-frontend/src/cognition/affectToCognition.js
  SapioCode/cognitcode-frontend/src/cognition/cognitiveSmoother.js

PURPOSE:
  Role 3's Face-API.js runs on the CLIENT and produces raw facial
  expressions (happy, sad, angry, fearful, surprised, neutral).
  The frontend converts these to cognitive states (engagement,
  frustration, confusion, boredom) and smooths them.

  This module replicates that pipeline SERVER-SIDE so that:
  1. The frontend can send RAW expressions and we compute cognitive state
  2. OR the frontend sends pre-computed cognitive state and we just smooth
  3. Either way the tutoring engine gets clean, stable affect data

The mapping formulas and smoother window size are IDENTICAL to Role 3's.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque


# ═══════════════════════════════════════════════════
# Affect → Cognition Mapping
# (mirrors cognitcode-frontend/src/cognition/affectToCognition.js)
# ═══════════════════════════════════════════════════

def _clamp(value: float) -> float:
    """Clamp value between 0.0 and 1.0"""
    return max(0.0, min(1.0, value))


def affect_to_cognition(expressions: dict) -> dict:
    """
    Convert raw Face-API.js expression scores to cognitive states.

    Input keys  (from face-api.js):
      happy, sad, angry, fearful, surprised, neutral  (each 0.0–1.0)

    Output keys (cognitive states):
      engagement, confusion, frustration, boredom  (each 0.0–1.0)

    The formulas are exact copies of Role 3's affectToCognition.js:
      engagement  = happy * 0.6  + surprised * 0.4
      confusion   = surprised * 0.6  + sad * 0.4
      frustration = angry * 0.5  + fearful * 0.3  + sad * 0.2
      boredom     = neutral * 0.8  - (happy + surprised) * 0.4
    """
    happy     = expressions.get("happy", 0.0)
    sad       = expressions.get("sad", 0.0)
    angry     = expressions.get("angry", 0.0)
    fearful   = expressions.get("fearful", 0.0)
    surprised = expressions.get("surprised", 0.0)
    neutral   = expressions.get("neutral", 0.0)

    engagement  = happy * 0.6 + surprised * 0.4
    confusion   = surprised * 0.6 + sad * 0.4
    frustration = angry * 0.5 + fearful * 0.3 + sad * 0.2
    boredom     = neutral * 0.8 - (happy + surprised) * 0.4

    return {
        "engagement":  _clamp(engagement),
        "confusion":   _clamp(confusion),
        "frustration": _clamp(frustration),
        "boredom":     _clamp(boredom)
    }


# ═══════════════════════════════════════════════════
# Cognitive Smoother
# (mirrors cognitcode-frontend/src/cognition/cognitiveSmoother.js)
# ═══════════════════════════════════════════════════

SMOOTHER_WINDOW_SIZE = 10  # Same as Role 3's WINDOW_SIZE


class CognitiveSmoother:
    """
    Moving-average smoother for cognitive state signals.
    Prevents the tutoring engine from reacting to momentary spikes.

    Window size = 10 samples (identical to Role 3's cognitiveSmoother.js).
    Face-API.js samples every 2 seconds, so this covers ~20 seconds of data.
    """

    def __init__(self, window_size: int = SMOOTHER_WINDOW_SIZE):
        self.window_size = window_size
        self._buffer: deque = deque(maxlen=window_size)

    def smooth(self, current_state: dict) -> dict:
        """
        Add a new cognitive state sample and return the smoothed average.

        Args:
            current_state: {engagement, confusion, frustration, boredom}

        Returns:
            Smoothed cognitive state dict
        """
        self._buffer.append(current_state)

        smoothed = {
            "engagement": 0.0,
            "confusion": 0.0,
            "frustration": 0.0,
            "boredom": 0.0
        }

        for state in self._buffer:
            smoothed["engagement"]  += state.get("engagement", 0.0)
            smoothed["confusion"]   += state.get("confusion", 0.0)
            smoothed["frustration"] += state.get("frustration", 0.0)
            smoothed["boredom"]     += state.get("boredom", 0.0)

        n = len(self._buffer)
        for key in smoothed:
            smoothed[key] = round(smoothed[key] / n, 4)

        return smoothed

    def get_current(self) -> dict:
        """Get the latest smoothed state without adding a new sample"""
        if not self._buffer:
            return {
                "engagement": 0.5,
                "confusion": 0.0,
                "frustration": 0.0,
                "boredom": 0.0
            }
        return self.smooth(self._buffer[-1])

    def reset(self):
        """Clear the smoother buffer (e.g., on session reset)"""
        self._buffer.clear()


# ═══════════════════════════════════════════════════
# Per-Student Affect Manager
# ═══════════════════════════════════════════════════

@dataclass
class AffectProfile:
    """Tracks a student's emotional state over time"""
    student_id: str
    smoother: CognitiveSmoother = field(default_factory=CognitiveSmoother)
    raw_expression_history: List[dict] = field(default_factory=list)
    cognitive_history: List[dict] = field(default_factory=list)
    peak_frustration: float = 0.0
    intervention_count: int = 0


class AffectAdapter:
    """
    Manages affect processing for all active students.

    Workflow:
    1. Frontend sends raw Face-API.js expressions → we convert + smooth
    2. OR Frontend sends pre-computed cognitive state → we just smooth
    3. Tutoring engine queries smoothed state for hint decisions
    """

    # Thresholds for pedagogical intervention (FR-6)
    FRUSTRATION_THRESHOLD_HIGH = 0.7    # Trigger gentle intervention
    FRUSTRATION_THRESHOLD_MODERATE = 0.4  # Adjust hint tone
    ENGAGEMENT_THRESHOLD_LOW = 0.2      # Student may be disengaged
    BOREDOM_THRESHOLD_HIGH = 0.6        # Increase challenge

    def __init__(self):
        self._profiles: Dict[str, AffectProfile] = {}

    def _get_profile(self, student_id: str) -> AffectProfile:
        if student_id not in self._profiles:
            self._profiles[student_id] = AffectProfile(student_id=student_id)
        return self._profiles[student_id]

    # ── Process raw expressions (from Face-API.js) ──
    def process_raw_expressions(self, student_id: str, expressions: dict) -> dict:
        """
        Accept raw Face-API.js output and return smoothed cognitive state.

        Args:
            student_id: Student identifier
            expressions: {happy, sad, angry, fearful, surprised, neutral}

        Returns:
            Smoothed {engagement, confusion, frustration, boredom}
        """
        profile = self._get_profile(student_id)

        # Step 1: Convert expressions → cognitive state
        cognitive = affect_to_cognition(expressions)

        # Step 2: Smooth
        smoothed = profile.smoother.smooth(cognitive)

        # Step 3: Track history
        profile.raw_expression_history.append(expressions)
        profile.cognitive_history.append(smoothed)
        if smoothed["frustration"] > profile.peak_frustration:
            profile.peak_frustration = smoothed["frustration"]

        return smoothed

    # ── Process pre-computed cognitive state ──
    def process_cognitive_state(self, student_id: str, cognitive_state: dict) -> dict:
        """
        Accept pre-computed cognitive state and return smoothed version.

        Args:
            student_id: Student identifier
            cognitive_state: {engagement, confusion, frustration, boredom}

        Returns:
            Smoothed cognitive state
        """
        profile = self._get_profile(student_id)
        smoothed = profile.smoother.smooth(cognitive_state)
        profile.cognitive_history.append(smoothed)
        if smoothed["frustration"] > profile.peak_frustration:
            profile.peak_frustration = smoothed["frustration"]
        return smoothed

    # ── Query current state ──
    def get_smoothed_state(self, student_id: str) -> dict:
        """Get the current smoothed cognitive state for a student"""
        profile = self._get_profile(student_id)
        return profile.smoother.get_current()

    # ── Intervention decisions (FR-6) ──
    def should_intervene(self, student_id: str) -> dict:
        """
        Decide if a pedagogical intervention is needed based on affect.

        Returns:
            {
                "intervene": bool,
                "reason": str,
                "action": str,  # "gentle_hint" | "simplify" | "challenge" | "none"
                "frustration": float,
                "engagement": float
            }
        """
        state = self.get_smoothed_state(student_id)
        frustration = state["frustration"]
        engagement  = state["engagement"]
        boredom     = state["boredom"]

        if frustration > self.FRUSTRATION_THRESHOLD_HIGH:
            return {
                "intervene": True,
                "reason": "high_frustration",
                "action": "gentle_hint",
                "frustration": frustration,
                "engagement": engagement,
                "tone": "empathetic",
                "hint_level_adjustment": +1  # escalate to more direct hint
            }

        if boredom > self.BOREDOM_THRESHOLD_HIGH and engagement < self.ENGAGEMENT_THRESHOLD_LOW:
            return {
                "intervene": True,
                "reason": "disengaged_bored",
                "action": "challenge",
                "frustration": frustration,
                "engagement": engagement,
                "tone": "energetic",
                "hint_level_adjustment": -1  # make hints less direct (more challenge)
            }

        if frustration > self.FRUSTRATION_THRESHOLD_MODERATE:
            return {
                "intervene": True,
                "reason": "moderate_frustration",
                "action": "soften_tone",
                "frustration": frustration,
                "engagement": engagement,
                "tone": "supportive",
                "hint_level_adjustment": 0
            }

        return {
            "intervene": False,
            "reason": "affect_normal",
            "action": "none",
            "frustration": frustration,
            "engagement": engagement,
            "tone": "neutral",
            "hint_level_adjustment": 0
        }

    # ── Hint tone adjustment ──
    def adjust_hint_tone(self, base_hint: str, student_id: str) -> str:
        """
        Modify the hint text based on the student's emotional state.

        High frustration → empathetic prefix + encouraging suffix
        Low engagement   → energetic prompt
        Normal           → no change
        """
        affect = self.should_intervene(student_id)

        if affect["tone"] == "empathetic":
            return (
                "I can see this is challenging — take a breath! 😊\n\n"
                + base_hint
                + "\n\nRemember: struggling is part of learning. You're doing great!"
            )
        elif affect["tone"] == "energetic":
            return (
                "Let's spice things up! 🚀\n\n"
                + base_hint
                + "\n\nTry thinking about this from a completely different angle."
            )
        elif affect["tone"] == "supportive":
            return base_hint + "\n\nYou're on the right track — keep going! 💪"

        return base_hint

    # ── Analytics for teacher dashboard ──
    def get_student_affect_summary(self, student_id: str) -> dict:
        """Summary for teacher dashboard"""
        profile = self._get_profile(student_id)
        current = profile.smoother.get_current()
        return {
            "student_id": student_id,
            "current_state": current,
            "peak_frustration": round(profile.peak_frustration, 4),
            "intervention_count": profile.intervention_count,
            "samples_collected": len(profile.cognitive_history),
            "is_at_risk": profile.peak_frustration > self.FRUSTRATION_THRESHOLD_HIGH
        }


# ── Singleton ──────────────────────────────────
_affect_adapter: Optional[AffectAdapter] = None


def get_affect_adapter() -> AffectAdapter:
    global _affect_adapter
    if _affect_adapter is None:
        _affect_adapter = AffectAdapter()
    return _affect_adapter
