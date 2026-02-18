"""
Phase 1 Integration Test — Tests BKT, Affect, and Bridge WITHOUT needing
Role 1/3 servers or a Groq API key.

Run:  python -m pytest tests/test_phase1_integration.py -v
"""
import pytest
import sys
import os

# ── Fix path so we can import app modules ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════
# TEST 1: Local BKT Engine  (mirrors Role 3's math)
# ═══════════════════════════════════════════════════════

class TestLocalBKT:
    """Verify the BKT math matches Role 3's implementation"""

    def test_bkt_correct_answer_increases_mastery(self):
        from app.services.bkt_local import bkt_update
        old = 0.3
        new = bkt_update(p_L=old, correct=True)
        assert new > old, f"Correct answer should increase mastery: {old} → {new}"

    def test_bkt_incorrect_answer_still_can_learn(self):
        from app.services.bkt_local import bkt_update
        old = 0.3
        new = bkt_update(p_L=old, correct=False)
        # BKT allows learning even on incorrect (via p_T), so new >= old possible
        assert 0.0 <= new <= 1.0, f"Mastery out of bounds: {new}"

    def test_bkt_high_mastery_stays_high_on_correct(self):
        from app.services.bkt_local import bkt_update
        old = 0.9
        new = bkt_update(p_L=old, correct=True)
        assert new >= old, f"High mastery should stay high on correct: {old} → {new}"

    def test_bkt_numerical_safety(self):
        from app.services.bkt_local import bkt_update
        # Edge cases
        assert 0.0 <= bkt_update(0.0, True) <= 1.0
        assert 0.0 <= bkt_update(1.0, False) <= 1.0
        assert 0.0 <= bkt_update(0.0, False) <= 1.0
        assert 0.0 <= bkt_update(1.0, True) <= 1.0

    def test_affect_fusion_engagement_boosts_learning(self):
        from app.services.bkt_local import modulate_bkt_params
        base = {"p_T": 0.1, "p_S": 0.1, "p_G": 0.2}
        modulated = modulate_bkt_params(base, {"engagement": 0.9, "frustration": 0.0, "confusion": 0.0, "boredom": 0.0})
        assert modulated["p_T"] > base["p_T"], "High engagement should boost learning rate"

    def test_affect_fusion_frustration_reduces_learning(self):
        from app.services.bkt_local import modulate_bkt_params
        base = {"p_T": 0.1, "p_S": 0.1, "p_G": 0.2}
        modulated = modulate_bkt_params(base, {"engagement": 0.0, "frustration": 0.9, "confusion": 0.0, "boredom": 0.0})
        assert modulated["p_T"] < base["p_T"], "High frustration should reduce learning rate"

    def test_affect_fusion_confusion_increases_slip(self):
        from app.services.bkt_local import modulate_bkt_params
        base = {"p_T": 0.1, "p_S": 0.1, "p_G": 0.2}
        modulated = modulate_bkt_params(base, {"engagement": 0.0, "frustration": 0.0, "confusion": 0.9, "boredom": 0.0})
        assert modulated["p_S"] > base["p_S"], "High confusion should increase slip probability"

    def test_affect_fusion_boredom_increases_guess(self):
        from app.services.bkt_local import modulate_bkt_params
        base = {"p_T": 0.1, "p_S": 0.1, "p_G": 0.2}
        modulated = modulate_bkt_params(base, {"engagement": 0.0, "frustration": 0.0, "confusion": 0.0, "boredom": 0.9})
        assert modulated["p_G"] > base["p_G"], "High boredom should increase guess probability"

    def test_affect_fusion_clamping(self):
        from app.services.bkt_local import modulate_bkt_params
        base = {"p_T": 0.1, "p_S": 0.1, "p_G": 0.2}
        # Extreme values
        modulated = modulate_bkt_params(base, {"engagement": 1.0, "frustration": 1.0, "confusion": 1.0, "boredom": 1.0})
        for key in ["p_T", "p_S", "p_G"]:
            assert 0.01 <= modulated[key] <= 0.9, f"{key} out of clamp range: {modulated[key]}"

    def test_explainability_high_frustration(self):
        from app.services.bkt_local import explain_bkt_update
        result = explain_bkt_update(
            cognitive_state={"frustration": 0.8, "engagement": 0.2, "confusion": 0.1, "boredom": 0.0},
            base_params={"p_T": 0.1, "p_S": 0.1, "p_G": 0.2},
            adapted_params={"p_T": 0.05, "p_S": 0.1, "p_G": 0.2},
            old_mastery=0.3,
            new_mastery=0.35
        )
        assert "frustration" in result["summary"].lower()

    def test_local_engine_full_pipeline(self):
        from app.services.bkt_local import LocalBKTEngine
        engine = LocalBKTEngine()

        results = engine.process_submission(
            student_id="test_student",
            concepts=["loops", "arrays"],
            correct=True,
            cognitive_state={"engagement": 0.8, "frustration": 0.1, "confusion": 0.1, "boredom": 0.0}
        )

        assert "loops" in results
        assert "arrays" in results
        assert results["loops"]["new_mastery"] > results["loops"]["old_mastery"]

    def test_local_engine_mastery_tracking(self):
        from app.services.bkt_local import LocalBKTEngine
        engine = LocalBKTEngine()

        # Submit correct multiple times → mastery should increase
        for _ in range(5):
            engine.process_submission("s1", ["recursion"], correct=True)

        mastery = engine.get_mastery("s1", "recursion")
        assert mastery > 0.5, f"After 5 correct submissions, mastery should be > 0.5, got {mastery}"

    def test_local_engine_weakest_concepts(self):
        from app.services.bkt_local import LocalBKTEngine
        engine = LocalBKTEngine()

        # One concept correct, one incorrect
        engine.process_submission("s2", ["easy_concept"], correct=True)
        engine.process_submission("s2", ["hard_concept"], correct=False)

        weakest = engine.get_weakest_concepts("s2")
        assert weakest[0] == "hard_concept"

    def test_local_engine_student_summary(self):
        from app.services.bkt_local import LocalBKTEngine
        engine = LocalBKTEngine()

        engine.process_submission("s3", ["loops"], correct=True)
        summary = engine.get_student_summary("s3")

        assert summary["student_id"] == "s3"
        assert summary["concepts_attempted"] == 1
        assert summary["total_submissions"] == 1


# ═══════════════════════════════════════════════════════
# TEST 2: Affect Adapter  (mirrors Role 3's frontend logic)
# ═══════════════════════════════════════════════════════

class TestAffectAdapter:
    """Verify affect processing matches Role 3's JS implementation"""

    def test_affect_to_cognition_happy(self):
        from app.services.affect_adapter import affect_to_cognition
        result = affect_to_cognition({"happy": 1.0, "sad": 0, "angry": 0, "fearful": 0, "surprised": 0, "neutral": 0})
        assert result["engagement"] == pytest.approx(0.6, abs=0.01)
        assert result["frustration"] == pytest.approx(0.0, abs=0.01)

    def test_affect_to_cognition_angry(self):
        from app.services.affect_adapter import affect_to_cognition
        result = affect_to_cognition({"happy": 0, "sad": 0, "angry": 1.0, "fearful": 0, "surprised": 0, "neutral": 0})
        assert result["frustration"] == pytest.approx(0.5, abs=0.01)

    def test_affect_to_cognition_neutral(self):
        from app.services.affect_adapter import affect_to_cognition
        result = affect_to_cognition({"happy": 0, "sad": 0, "angry": 0, "fearful": 0, "surprised": 0, "neutral": 1.0})
        assert result["boredom"] == pytest.approx(0.8, abs=0.01)

    def test_affect_to_cognition_mixed(self):
        from app.services.affect_adapter import affect_to_cognition
        # Exact formula: engagement = happy*0.6 + surprised*0.4
        result = affect_to_cognition({"happy": 0.5, "sad": 0.2, "angry": 0.1, "fearful": 0.1, "surprised": 0.3, "neutral": 0.1})
        expected_engagement = 0.5 * 0.6 + 0.3 * 0.4  # 0.42
        assert result["engagement"] == pytest.approx(expected_engagement, abs=0.01)

    def test_smoother_window(self):
        from app.services.affect_adapter import CognitiveSmoother
        smoother = CognitiveSmoother(window_size=3)

        # Feed 3 samples
        smoother.smooth({"engagement": 0.9, "confusion": 0.1, "frustration": 0.1, "boredom": 0.0})
        smoother.smooth({"engagement": 0.3, "confusion": 0.7, "frustration": 0.5, "boredom": 0.0})
        result = smoother.smooth({"engagement": 0.6, "confusion": 0.4, "frustration": 0.3, "boredom": 0.0})

        # Average of 3 samples
        assert result["engagement"] == pytest.approx((0.9 + 0.3 + 0.6) / 3, abs=0.01)

    def test_adapter_intervention_high_frustration(self):
        from app.services.affect_adapter import AffectAdapter
        adapter = AffectAdapter()

        # Send high frustration
        adapter.process_cognitive_state("s1", {
            "frustration": 0.9, "engagement": 0.1, "confusion": 0.3, "boredom": 0.0
        })

        decision = adapter.should_intervene("s1")
        assert decision["intervene"] is True
        assert decision["action"] == "gentle_hint"

    def test_adapter_intervention_bored(self):
        from app.services.affect_adapter import AffectAdapter
        adapter = AffectAdapter()

        adapter.process_cognitive_state("s2", {
            "frustration": 0.0, "engagement": 0.1, "confusion": 0.0, "boredom": 0.8
        })

        decision = adapter.should_intervene("s2")
        assert decision["intervene"] is True
        assert decision["action"] == "challenge"

    def test_adapter_no_intervention_normal(self):
        from app.services.affect_adapter import AffectAdapter
        adapter = AffectAdapter()

        adapter.process_cognitive_state("s3", {
            "frustration": 0.1, "engagement": 0.7, "confusion": 0.1, "boredom": 0.0
        })

        decision = adapter.should_intervene("s3")
        assert decision["intervene"] is False

    def test_hint_tone_empathetic(self):
        from app.services.affect_adapter import AffectAdapter
        adapter = AffectAdapter()

        adapter.process_cognitive_state("s4", {
            "frustration": 0.9, "engagement": 0.1, "confusion": 0.3, "boredom": 0.0
        })

        adjusted = adapter.adjust_hint_tone("Try using a loop here.", "s4")
        assert "take a breath" in adjusted.lower() or "challenging" in adjusted.lower()


# ═══════════════════════════════════════════════════════
# TEST 3: Integration Bridge (no network, no API key)
# ═══════════════════════════════════════════════════════

class TestIntegrationBridge:
    """Test bridge logic without needing external services"""

    def test_infer_concepts_from_recursive_code(self):
        from app.services.integration_bridge import IntegrationBridge
        from app.services.code_analyzer import CodeAnalyzer

        bridge = IntegrationBridge()
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        analysis = bridge.analyzer.analyze_python(code)
        concepts = bridge._infer_concepts(analysis)
        assert "recursion" in concepts
        assert "functions" in concepts

    def test_infer_concepts_from_loop_code(self):
        from app.services.integration_bridge import IntegrationBridge

        bridge = IntegrationBridge()
        code = """
def sum_list(nums):
    total = 0
    for n in nums:
        total += n
    return total
"""
        analysis = bridge.analyzer.analyze_python(code)
        concepts = bridge._infer_concepts(analysis)
        assert "loops" in concepts
        assert "functions" in concepts

    def test_local_execution_ok(self):
        from app.services.integration_bridge import IntegrationBridge

        bridge = IntegrationBridge()
        result = bridge._execute_locally("print('hello')")
        assert result.status == "OK"
        assert "hello" in result.stdout

    def test_local_execution_rte(self):
        from app.services.integration_bridge import IntegrationBridge

        bridge = IntegrationBridge()
        result = bridge._execute_locally("raise ValueError('boom')")
        assert result.status == "RTE"
        assert "boom" in result.stderr

    def test_local_execution_tle(self):
        from app.services.integration_bridge import IntegrationBridge

        bridge = IntegrationBridge()
        result = bridge._execute_locally("while True: pass")
        assert result.status == "TLE"

    def test_hint_history_tracking(self):
        from app.services.integration_bridge import IntegrationBridge
        from app.services.tutoring_engine import HintLevel

        bridge = IntegrationBridge()
        bridge._record_hint("s1", "Try a loop", HintLevel.SOCRATIC_QUESTION, "stuck")
        bridge._record_hint("s1", "Use for..in", HintLevel.CONCEPTUAL_NUDGE, "still_stuck")

        history = bridge.get_hint_history("s1")
        assert len(history) == 2
        assert history[0]["level"] == 1
        assert history[1]["level"] == 2


# ═══════════════════════════════════════════════════════
# TEST 4: End-to-End BKT + Affect Pipeline
# ═══════════════════════════════════════════════════════

class TestEndToEndPipeline:
    """Integration test combining BKT + Affect"""

    def test_frustrated_student_gets_lower_learning_rate(self):
        from app.services.bkt_local import LocalBKTEngine

        engine = LocalBKTEngine()

        # Student A: calm, correct answer
        result_calm = engine.process_submission(
            "calm_student", ["loops"], correct=True,
            cognitive_state={"engagement": 0.8, "frustration": 0.0, "confusion": 0.0, "boredom": 0.0}
        )

        # Student B: frustrated, correct answer
        result_frust = engine.process_submission(
            "frust_student", ["loops"], correct=True,
            cognitive_state={"engagement": 0.1, "frustration": 0.9, "confusion": 0.3, "boredom": 0.0}
        )

        # Calm student should gain MORE mastery than frustrated student
        calm_gain = result_calm["loops"]["delta"]
        frust_gain = result_frust["loops"]["delta"]
        assert calm_gain > frust_gain, (
            f"Calm student gain ({calm_gain}) should exceed frustrated student gain ({frust_gain})"
        )

    def test_mastery_drives_hint_level(self):
        """Low mastery → should escalate to more direct hints"""
        from app.services.bkt_local import LocalBKTEngine
        from app.services.tutoring_engine import TutoringEngine, StudentContext, HintLevel

        engine = LocalBKTEngine()
        tutor = TutoringEngine()

        # Submit many wrong answers → low mastery
        for _ in range(5):
            engine.process_submission("struggling", ["recursion"], correct=False)

        mastery = engine.get_mastery("struggling", "recursion")
        assert mastery < 0.5, f"Should have low mastery after 5 wrong: {mastery}"

        # Tutoring engine should intervene
        ctx = StudentContext(
            problem_description="Implement factorial",
            current_code="def f(n): return n",
            time_stuck=120,
            frustration_level=0.6,
            previous_hints=2,
            code_attempts=5
        )
        decision = tutor.decide_intervention(ctx)
        assert decision.should_intervene is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
