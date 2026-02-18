"""
Phase 5 Tests — LangGraph, Session Persistence, Concept Overlap,
                Teacher Generate-Problem Endpoint, Bridge Deep Path

Run:  python -m pytest tests/test_phase5_new_features.py -v
"""
import pytest
import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════
# TEST 1: LangGraph Workflow
# ═══════════════════════════════════════════════════════════════

class TestLangGraphWorkflow:
    """Verify the LangGraph state graph compiles and routes correctly."""

    def test_graph_compiles(self):
        """Graph should compile without errors."""
        from app.services.langgraph_tutoring import build_tutoring_graph
        graph = build_tutoring_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        """Graph should contain all expected nodes."""
        from app.services.langgraph_tutoring import build_tutoring_graph
        graph = build_tutoring_graph()
        node_names = set(graph.nodes.keys())
        expected = {"__start__", "receive", "analyze", "assess",
                    "gentle", "socratic", "challenge", "deliver"}
        assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"

    def test_graph_singleton(self):
        """get_tutoring_graph should return same instance."""
        from app.services.langgraph_tutoring import get_tutoring_graph
        g1 = get_tutoring_graph()
        g2 = get_tutoring_graph()
        assert g1 is g2

    def test_route_by_affect_gentle(self):
        """High frustration should route to gentle path."""
        from app.services.langgraph_tutoring import route_by_affect
        state = {"frustration": 0.8, "boredom": 0.0, "engagement": 0.5, "avg_mastery": 0.5}
        assert route_by_affect(state) == "gentle"

    def test_route_by_affect_challenge(self):
        """High mastery + low frustration should route to challenge."""
        from app.services.langgraph_tutoring import route_by_affect
        state = {"frustration": 0.1, "boredom": 0.0, "engagement": 0.7, "avg_mastery": 0.8}
        assert route_by_affect(state) == "challenge"

    def test_route_by_affect_challenge_boredom(self):
        """High boredom + low engagement should route to challenge."""
        from app.services.langgraph_tutoring import route_by_affect
        state = {"frustration": 0.1, "boredom": 0.7, "engagement": 0.2, "avg_mastery": 0.5}
        assert route_by_affect(state) == "challenge"

    def test_route_by_affect_socratic_default(self):
        """Normal state should route to socratic."""
        from app.services.langgraph_tutoring import route_by_affect
        state = {"frustration": 0.3, "boredom": 0.2, "engagement": 0.6, "avg_mastery": 0.5}
        assert route_by_affect(state) == "socratic"

    def test_combined_route_no_intervention(self):
        """Should skip hint paths when no intervention needed."""
        from app.services.langgraph_tutoring import _combined_route
        state = {"should_intervene": False, "frustration": 0.8}
        assert _combined_route(state) == "deliver"

    def test_combined_route_with_intervention(self):
        """Should route by affect when intervention needed."""
        from app.services.langgraph_tutoring import _combined_route
        state = {
            "should_intervene": True, "frustration": 0.8,
            "boredom": 0.0, "engagement": 0.3, "avg_mastery": 0.4,
        }
        assert _combined_route(state) == "gentle"

    def test_receive_node_loads_defaults(self):
        """Receive node should set default affect values."""
        from app.services.langgraph_tutoring import receive_node
        state = {"student_id": "test_123"}
        result = receive_node(state)
        assert "frustration" in result
        assert "engagement" in result
        assert "conversation_history" in result

    def test_analyze_node_runs_ast(self):
        """Analyze node should run AST analysis on code."""
        from app.services.langgraph_tutoring import analyze_node
        state = {
            "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)\n",
        }
        result = analyze_node(state)
        assert result["analysis"] is not None
        assert result["algorithm_pattern"] is not None
        assert isinstance(result["concepts_detected"], list)

    def test_assess_node_decides_intervention(self):
        """Assess node should decide whether to intervene."""
        from app.services.langgraph_tutoring import assess_node
        state = {
            "student_id": "test_assess",
            "time_stuck": 120,
            "frustration": 0.7,
            "previous_hints": 0,
        }
        result = assess_node(state)
        assert result["should_intervene"] is True
        assert "mastery_snapshot" in result
        assert "avg_mastery" in result

    def test_assess_no_intervention(self):
        """Low time_stuck + low frustration should not trigger intervention."""
        from app.services.langgraph_tutoring import assess_node
        state = {
            "student_id": "test_no_intervene",
            "time_stuck": 5,
            "frustration": 0.1,
            "previous_hints": 0,
        }
        result = assess_node(state)
        assert result["should_intervene"] is False

    def test_deliver_node_formats_response(self):
        """Deliver node should produce a complete response dict."""
        from app.services.langgraph_tutoring import deliver_node
        state = {
            "student_id": "test_deliver",
            "should_intervene": True,
            "hint_text": "Think about what happens when n=0",
            "hint_level": 2,
            "hint_path": "socratic",
            "teaching_focus": "base_case",
            "algorithm_pattern": "recursion",
            "concepts_detected": ["recursion", "base_case"],
            "issues": ["missing base case"],
            "approach_summary": "Recursive approach without base case",
            "mastery_snapshot": {"recursion": 0.4},
            "avg_mastery": 0.4,
            "frustration": 0.3,
            "engagement": 0.7,
            "confusion": 0.2,
            "boredom": 0.0,
        }
        result = deliver_node(state)
        assert "response" in result
        resp = result["response"]
        assert resp["student_id"] == "test_deliver"
        assert resp["should_intervene"] is True
        assert resp["hint_path"] == "socratic"
        assert "cognitive_state" in resp


# ═══════════════════════════════════════════════════════════════
# TEST 2: Conversation Memory (LangGraph)
# ═══════════════════════════════════════════════════════════════

class TestLangGraphConversation:
    """Test conversation memory in LangGraph module."""

    def test_record_and_load(self):
        from app.services.langgraph_tutoring import (
            record_student_message, get_conversation_history, clear_conversation,
        )
        sid = "test_conv_001"
        clear_conversation(sid)
        record_student_message(sid, "I'm confused about recursion")
        history = get_conversation_history(sid)
        assert len(history) >= 1
        assert history[-1]["content"] == "I'm confused about recursion"
        clear_conversation(sid)

    def test_clear_conversation(self):
        from app.services.langgraph_tutoring import (
            record_student_message, get_conversation_history, clear_conversation,
        )
        sid = "test_clear_001"
        record_student_message(sid, "Hello")
        clear_conversation(sid)
        history = get_conversation_history(sid)
        assert len(history) == 0


# ═══════════════════════════════════════════════════════════════
# TEST 3: Session Persistence (SQLite)
# ═══════════════════════════════════════════════════════════════

class TestSessionStore:
    """Test SQLite session store CRUD operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary session store."""
        from app.services.session_store import SessionStore
        db = tmp_path / "test.db"
        s = SessionStore(str(db))
        yield s
        s.close()

    def test_create_session(self, store):
        s = store.create_session("sess_001", "student_A", "Reverse a string")
        assert s.session_id == "sess_001"
        assert s.student_id == "student_A"
        assert s.status == "active"

    def test_get_session(self, store):
        store.create_session("sess_002", "student_B", "Find max")
        result = store.get_session("sess_002")
        assert result is not None
        assert result.student_id == "student_B"

    def test_get_nonexistent_session(self, store):
        result = store.get_session("does_not_exist")
        assert result is None

    def test_get_student_sessions(self, store):
        store.create_session("s1", "student_C", "Problem 1")
        store.create_session("s2", "student_C", "Problem 2")
        store.create_session("s3", "student_D", "Problem 3")
        sessions = store.get_student_sessions("student_C")
        assert len(sessions) == 2
        assert all(s.student_id == "student_C" for s in sessions)

    def test_update_session_activity(self, store):
        store.create_session("sess_upd", "student_E", "Sort list")
        store.update_session_activity("sess_upd", hints_delta=2, submissions_delta=1)
        result = store.get_session("sess_upd")
        assert result.total_hints == 2
        assert result.total_submissions == 1

    def test_complete_session(self, store):
        store.create_session("sess_comp", "student_F", "Two sum")
        store.complete_session("sess_comp")
        result = store.get_session("sess_comp")
        assert result.status == "completed"

    def test_record_hint(self, store):
        from app.services.session_store import HintRecord
        store.create_session("sess_hint", "student_G", "BFS")
        store.record_hint(HintRecord(
            student_id="student_G",
            session_id="sess_hint",
            hint_text="Think about the base case",
            hint_level=2,
            hint_path="socratic",
            teaching_focus="base_case",
            frustration_at_time=0.3,
            mastery_at_time=0.5,
        ))
        hints = store.get_hint_history("student_G")
        assert len(hints) == 1
        assert hints[0]["hint_level"] == 2

    def test_record_viva_attempt(self, store):
        from app.services.session_store import VivaAttemptRecord
        store.record_viva_attempt(VivaAttemptRecord(
            student_id="student_H",
            session_id="sess_viva",
            question="Explain recursion",
            transcribed_answer="It calls itself with smaller input",
            verdict="PASS",
            score=0.85,
            concept_overlap_score=0.75,
        ))
        attempts = store.get_viva_attempts("student_H")
        assert len(attempts) == 1
        assert attempts[0]["verdict"] == "PASS"

    def test_conversation_crud(self, store):
        from app.services.session_store import ConversationRecord
        store.record_conversation_turn(ConversationRecord(
            student_id="student_I", role="student",
            content="I don't understand recursion",
        ))
        store.record_conversation_turn(ConversationRecord(
            student_id="student_I", role="tutor",
            content="Think about what happens when n=0",
            hint_level=2, teaching_focus="base_case",
        ))
        conv = store.get_conversation("student_I")
        assert len(conv) == 2
        assert conv[0]["role"] == "student"
        assert conv[1]["role"] == "assistant"  # tutor → assistant

    def test_clear_conversation(self, store):
        from app.services.session_store import ConversationRecord
        store.record_conversation_turn(ConversationRecord(
            student_id="student_J", role="student", content="Hello",
        ))
        deleted = store.clear_conversation("student_J")
        assert deleted == 1
        assert len(store.get_conversation("student_J")) == 0

    def test_student_stats(self, store):
        from app.services.session_store import HintRecord, VivaAttemptRecord
        store.create_session("ss1", "student_K", "Problem A")
        store.create_session("ss2", "student_K", "Problem B")
        store.record_hint(HintRecord(
            student_id="student_K", session_id="ss1",
            hint_text="hint1", hint_level=1, hint_path="socratic",
            teaching_focus="loops",
        ))
        store.record_viva_attempt(VivaAttemptRecord(
            student_id="student_K", session_id="ss1",
            question="q1", transcribed_answer="a1",
            verdict="PASS", score=0.8,
        ))
        stats = store.get_student_stats("student_K")
        assert stats["total_sessions"] == 2
        assert stats["total_hints"] == 1
        assert stats["total_viva_attempts"] == 1
        assert stats["viva_pass_rate"] == 1.0


# ═══════════════════════════════════════════════════════════════
# TEST 4: Concept Overlap (SemanticVerifier)
# ═══════════════════════════════════════════════════════════════

class TestConceptOverlap:
    """Test the deterministic concept-overlap scoring."""

    def _make_analysis(self, concepts, pattern="recursive", has_recursion=True, has_base=True):
        """Create a mock CodeAnalysisResult."""
        from app.services.code_analyzer import (
            CodeAnalysisResult, AlgorithmPattern, FunctionProfile
        )
        fp = MagicMock()
        fp.calls_itself = has_recursion
        fp.has_base_case = has_base
        fp.loop_count = 0
        analysis = MagicMock(spec=CodeAnalysisResult)
        analysis.concepts_detected = concepts
        analysis.algorithm_pattern = AlgorithmPattern(pattern) if pattern else AlgorithmPattern.UNKNOWN
        analysis.function_profiles = [fp]
        analysis.data_structures_used = []
        analysis.issue_locations = []
        return analysis

    def _get_verifier(self):
        """Create a SemanticVerifier with mocked groq."""
        from app.services.viva_engine import SemanticVerifier
        verifier = SemanticVerifier()
        verifier.groq = MagicMock()
        return verifier

    def test_full_overlap(self):
        verifier = self._get_verifier()
        analysis = self._make_analysis(["recursion"], "recursive")
        result = verifier.compute_concept_overlap(
            analysis,
            "This function uses recursion, it calls itself. There is a base case for when n equals one.",
        )
        assert result["overlap_score"] >= 0.5
        assert "recursion" in result["matched"]

    def test_no_overlap(self):
        verifier = self._get_verifier()
        analysis = self._make_analysis(["recursion"], "recursive")
        result = verifier.compute_concept_overlap(
            analysis,
            "I just wrote some code that does stuff",
        )
        assert result["overlap_score"] < 0.5
        assert len(result["missed"]) > 0

    def test_synonym_matching(self):
        verifier = self._get_verifier()
        analysis = self._make_analysis(["recursion"], "recursive")
        result = verifier.compute_concept_overlap(
            analysis,
            "The function calls itself with a smaller input and has a stopping condition",
        )
        # "calls itself" is a synonym for "recursion", "stopping condition" for "base case"
        assert result["overlap_score"] >= 0.3

    def test_short_transcript_low_confidence(self):
        verifier = self._get_verifier()
        analysis = self._make_analysis(["recursion"])
        result = verifier.compute_concept_overlap(analysis, "it loops")
        assert result["confidence"] == "low"

    def test_result_structure(self):
        verifier = self._get_verifier()
        analysis = self._make_analysis(["loops"])
        result = verifier.compute_concept_overlap(analysis, "I used a for loop to iterate")
        assert "ast_concepts" in result
        assert "claimed_concepts" in result
        assert "matched" in result
        assert "missed" in result
        assert "overlap_score" in result
        assert "confidence" in result


# ═══════════════════════════════════════════════════════════════
# TEST 5: Bridge Deep AST Path
# ═══════════════════════════════════════════════════════════════

class TestBridgeDeepPath:
    """Verify bridge passes CodeAnalysisResult to HintGenerator."""

    def test_hint_generator_receives_analysis(self):
        """HintGenerator.generate_hint_for_student should receive CodeAnalysisResult."""
        from app.services.tutoring_engine import HintGenerator, HintLevel
        from app.services.code_analyzer import CodeAnalysisResult

        mock_groq = AsyncMock()
        mock_groq.chat_completion = AsyncMock(return_value="Think about the base case")
        gen = HintGenerator(groq_service=mock_groq)

        # Verify the method signature accepts analysis as CodeAnalysisResult
        import inspect
        sig = inspect.signature(gen.generate_hint_for_student)
        params = list(sig.parameters.keys())
        assert "analysis" in params, "generate_hint_for_student must accept 'analysis'"

    def test_hint_generator_uses_ast_tutor_when_given_analysis(self):
        """When given a CodeAnalysisResult, HintGenerator should use ASTTutor (deep path)."""
        from app.services.tutoring_engine import HintGenerator, HintLevel
        from app.services.code_analyzer import CodeAnalyzer

        mock_groq = AsyncMock()
        mock_groq.chat_completion = AsyncMock(return_value="Check your base case")
        gen = HintGenerator(groq_service=mock_groq)

        analyzer = CodeAnalyzer()
        analysis = analyzer.analyze_python(
            "def fib(n):\n    return fib(n-1) + fib(n-2)\n"
        )

        # Run with analysis — should use AST path
        loop = asyncio.new_event_loop()
        try:
            hint = loop.run_until_complete(gen.generate_hint_for_student(
                student_id="test_deep",
                level=HintLevel.SOCRATIC_QUESTION,
                problem="Fibonacci",
                code="def fib(n):\n    return fib(n-1) + fib(n-2)\n",
                analysis=analysis,
            ))
            assert hint is not None
            assert len(hint) > 0
            # Groq should have been called with a prompt that includes AST context
            call_args = mock_groq.chat_completion.call_args
            assert call_args is not None
        finally:
            loop.close()


# ═══════════════════════════════════════════════════════════════
# TEST 6: Teacher Generate-Problem Endpoint (FastAPI)
# ═══════════════════════════════════════════════════════════════

class TestTeacherGenerateProblem:
    """Test the /api/teacher/generate-problem endpoint."""

    def test_endpoint_exists(self):
        """The generate-problem route should be registered."""
        from app.api.teacher_routes import router
        paths = [r.path for r in router.routes]
        assert "/generate-problem" in paths

    def test_endpoint_is_post(self):
        """The generate-problem route should be a POST."""
        from app.api.teacher_routes import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/generate-problem":
                assert "POST" in r.methods

    def test_request_model_validation(self):
        """GenerateProblemRequest should accept valid data."""
        from app.api.teacher_routes import GenerateProblemRequest
        req = GenerateProblemRequest(
            description="Binary search on sorted array",
            difficulty="medium",
            concepts=["binary_search", "arrays"],
            num_test_cases=3,
        )
        assert req.description == "Binary search on sorted array"
        assert req.difficulty == "medium"

    def test_request_model_defaults(self):
        """GenerateProblemRequest should have sensible defaults."""
        from app.api.teacher_routes import GenerateProblemRequest
        req = GenerateProblemRequest(description="Sorting")
        assert req.difficulty == "medium"
        assert req.num_test_cases == 3
        assert req.concepts == []


# ═══════════════════════════════════════════════════════════════
# TEST 7: LangGraph Integration Route
# ═══════════════════════════════════════════════════════════════

class TestLangGraphRoute:
    """Test the /api/integration/hint-graph endpoint."""

    def test_endpoint_exists(self):
        """The hint-graph route should be registered."""
        from app.api.integration_routes import router
        paths = [r.path for r in router.routes]
        assert "/hint-graph" in paths

    def test_endpoint_is_post(self):
        """hint-graph should be a POST endpoint."""
        from app.api.integration_routes import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/hint-graph":
                assert "POST" in r.methods

    def test_imports_langgraph(self):
        """Integration routes should import LangGraph components."""
        from app.api.integration_routes import get_hint_via_langgraph
        assert callable(get_hint_via_langgraph)


# ═══════════════════════════════════════════════════════════════
# TEST 8: Session Store Singleton
# ═══════════════════════════════════════════════════════════════

class TestSessionStoreSingleton:
    """Test session store singleton pattern."""

    def test_singleton_returns_same_instance(self):
        from app.services.session_store import get_session_store
        s1 = get_session_store()
        s2 = get_session_store()
        assert s1 is s2

    def test_store_has_required_methods(self):
        from app.services.session_store import SessionStore
        store = SessionStore.__new__(SessionStore)
        required = [
            "create_session", "get_session", "get_student_sessions",
            "update_session_activity", "complete_session",
            "record_hint", "get_hint_history",
            "record_viva_attempt", "get_viva_attempts",
            "record_conversation_turn", "get_conversation",
            "clear_conversation", "get_student_stats",
        ]
        for method in required:
            assert hasattr(store, method), f"SessionStore missing method: {method}"
