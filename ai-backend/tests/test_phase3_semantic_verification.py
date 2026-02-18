"""
Phase 3 Tests — AST-Driven Semantic Verification (Viva Voce)

Validates:
  - QuestionGenerator uses FunctionProfile (recursive, base-case aware)
  - QuestionGenerator uses algorithm_pattern for why-choice questions
  - QuestionGenerator uses issue_locations to target code defects
  - SemanticVerifier builds enriched prompts with AST ground truth
  - Fallback keyword verification works without LLM
  - Full VivaEngine session flow works end-to-end (mocked LLM)
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.code_analyzer import CodeAnalyzer, AlgorithmPattern, CodeIssue
from app.services.viva_engine import (
    QuestionGenerator, SemanticVerifier, VivaEngine,
    VivaQuestion, StudentAnswer, VivaVerdict, QuestionType,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures & test data
# ═══════════════════════════════════════════════════════════════

RECURSIVE_CODE = """\
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

BROKEN_RECURSIVE = """\
def bad_count(n):
    return n + bad_count(n - 1)
"""

LOOP_CODE = """\
def find_max(nums):
    result = 0
    for x in nums:
        if x > result:
            result = x
    return result
"""

INFINITE_LOOP_CODE = """\
def broken():
    while True:
        print("oops")
"""


@pytest.fixture
def analyzer():
    return CodeAnalyzer()


@pytest.fixture
def gen():
    return QuestionGenerator()


@pytest.fixture
def verifier():
    v = SemanticVerifier()
    v.groq = MagicMock()
    return v


@pytest.fixture
def engine():
    e = VivaEngine()
    e.verifier.groq = MagicMock()
    return e


# ═══════════════════════════════════════════════════════════════
# Group A — QuestionGenerator (Phase 3 enhanced)
# ═══════════════════════════════════════════════════════════════

class TestQuestionGeneratorPhase3:

    def test_generates_questions_list(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=3)
        assert isinstance(qs, list)
        assert 1 <= len(qs) <= 3

    def test_questions_have_ids(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=3)
        for q in qs:
            assert q.id.startswith("q")

    def test_recursive_code_generates_recursion_concepts(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=5)
        all_concepts = [c for q in qs for c in q.expected_concepts]
        assert any(c in ("recursion", "base_case", "call_stack") for c in all_concepts)

    def test_broken_recursive_generates_base_case_question(self, gen, analyzer):
        analysis = analyzer.analyze_python(BROKEN_RECURSIVE)
        qs = gen.generate_questions(BROKEN_RECURSIVE, analysis, num_questions=5)
        all_text = " ".join(q.question_text for q in qs).lower()
        # Should ask about what stops recursion
        assert any(w in all_text for w in ["base case", "stop", "recursion", "terminat"])

    def test_recursive_question_has_higher_difficulty(self, gen, analyzer):
        """Broken recursion (no base case) should get difficulty >= 2."""
        analysis = analyzer.analyze_python(BROKEN_RECURSIVE)
        qs = gen.generate_questions(BROKEN_RECURSIVE, analysis, num_questions=5)
        fn_qs = [q for q in qs if q.question_type == QuestionType.FUNCTION_PURPOSE]
        if fn_qs:
            assert any(q.difficulty >= 2 for q in fn_qs)

    def test_algorithm_pattern_question_generated(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=5)
        why_qs = [q for q in qs if q.question_type == QuestionType.WHY_CHOICE]
        assert len(why_qs) >= 1

    def test_algorithm_pattern_concepts_include_ast_concepts(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=5)
        why_qs = [q for q in qs if q.question_type == QuestionType.WHY_CHOICE]
        if why_qs:
            all_concepts = [c for q in why_qs for c in q.expected_concepts]
            # The AST detects "recursion" for factorial — should appear in expected_concepts
            assert "recursion" in all_concepts or "base_case" in all_concepts

    def test_issue_question_references_line(self, gen, analyzer):
        analysis = analyzer.analyze_python(INFINITE_LOOP_CODE)
        qs = gen.generate_questions(INFINITE_LOOP_CODE, analysis, num_questions=5)
        # At least one question should reference a specific line number
        line_qs = [q for q in qs if q.target_line is not None]
        assert len(line_qs) >= 1

    def test_loop_code_question_mentions_loop(self, gen, analyzer):
        analysis = analyzer.analyze_python(LOOP_CODE)
        qs = gen.generate_questions(LOOP_CODE, analysis, num_questions=5)
        all_text = " ".join(q.question_text for q in qs).lower()
        assert any(w in all_text for w in ["loop", "iterate", "for", "while", "result"])

    def test_num_questions_limit_respected(self, gen, analyzer):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        qs = gen.generate_questions(RECURSIVE_CODE, analysis, num_questions=2)
        assert len(qs) <= 2


# ═══════════════════════════════════════════════════════════════
# Group B — SemanticVerifier prompt building
# ═══════════════════════════════════════════════════════════════

class TestSemanticVerifierPromptBuilding:
    """Test that the verifier's prompt includes AST ground truth."""

    def _make_qa(self, q_text="What does factorial do?", response="It multiplies numbers"):
        q = VivaQuestion(
            id="q1",
            question_type=QuestionType.FUNCTION_PURPOSE,
            question_text=q_text,
            target_code="def factorial(n): ...",
            target_line=None,
            expected_concepts=["recursion", "base_case"],
            difficulty=1,
        )
        a = StudentAnswer(
            question_id="q1",
            transcribed_text=response,
            audio_duration_seconds=5.0,
        )
        return q, a

    @pytest.mark.asyncio
    async def test_verify_with_ast_analysis_enriches_prompt(self, verifier, analyzer):
        """The LLM call must receive a prompt containing AST info."""
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        q, a = self._make_qa()

        captured = []
        async def mock_chat(*args, **kwargs):
            captured.extend(args[0] if args else kwargs.get("messages", []))
            return json.dumps({
                "score": 0.8,
                "matched_concepts": ["recursion"],
                "missing_concepts": [],
                "understanding_level": "strong",
                "feedback": "Good",
                "red_flags": [],
            })
        verifier.groq.chat_completion = mock_chat

        await verifier.verify_answer(q, a, RECURSIVE_CODE, analysis)

        full_text = " ".join(m.get("content", "") for m in captured)
        # Must include AST ground-truth fields
        assert "recursive" in full_text.lower() or "recursion" in full_text.lower()
        assert "algorithm" in full_text.lower() or "ast" in full_text.lower()

    @pytest.mark.asyncio
    async def test_verify_without_analysis_uses_unknown_fallback(self, verifier):
        q, a = self._make_qa()

        captured = []
        async def mock_chat(*args, **kwargs):
            captured.extend(args[0] if args else kwargs.get("messages", []))
            return json.dumps({
                "score": 0.5,
                "matched_concepts": [],
                "missing_concepts": ["recursion"],
                "understanding_level": "adequate",
                "feedback": "Ok",
                "red_flags": [],
            })
        verifier.groq.chat_completion = mock_chat

        await verifier.verify_answer(q, a, RECURSIVE_CODE, None)
        full_text = " ".join(m.get("content", "") for m in captured)
        assert "unknown" in full_text.lower()

    @pytest.mark.asyncio
    async def test_verify_returns_answer_evaluation(self, verifier, analyzer):
        from app.services.viva_engine import AnswerEvaluation
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        q, a = self._make_qa()

        async def mock_chat(*args, **kwargs):
            return json.dumps({
                "score": 0.85,
                "matched_concepts": ["recursion", "base_case"],
                "missing_concepts": [],
                "understanding_level": "strong",
                "feedback": "Excellent explanation.",
                "red_flags": [],
            })
        verifier.groq.chat_completion = mock_chat

        result = await verifier.verify_answer(q, a, RECURSIVE_CODE, analysis)
        assert isinstance(result, AnswerEvaluation)
        assert result.score == pytest.approx(0.85)
        assert result.is_acceptable is True

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_keyword_matching(self, verifier):
        """If the LLM raises, fallback keyword matching is used."""
        q, a = self._make_qa(response="recursion is when a function calls itself")

        async def boom(*args, **kwargs):
            raise RuntimeError("LLM down")
        verifier.groq.chat_completion = boom

        result = await verifier.verify_answer(q, a, RECURSIVE_CODE)
        # fallback should match "recursion" keyword
        assert "recursion" in result.matched_concepts
        assert result.score > 0


# ═══════════════════════════════════════════════════════════════
# Group C — Full VivaEngine session flow
# ═══════════════════════════════════════════════════════════════

class TestVivaEngineFlow:

    def _mock_groq(self, engine, score=0.8):
        async def mock_chat(*args, **kwargs):
            return json.dumps({
                "score": score,
                "matched_concepts": ["recursion"],
                "missing_concepts": [],
                "understanding_level": "strong",
                "feedback": "Good",
                "red_flags": [],
            })
        engine.verifier.groq.chat_completion = mock_chat

    def test_start_session_creates_session(self, engine):
        session = engine.start_session("sess1", "stu1", RECURSIVE_CODE, num_questions=2)
        assert session.session_id == "sess1"
        assert len(session.questions) <= 2
        assert session.verdict is None

    def test_start_session_generates_questions(self, engine):
        session = engine.start_session("sess2", "stu2", RECURSIVE_CODE, num_questions=3)
        assert len(session.questions) >= 1

    def test_get_current_question_returns_first(self, engine):
        engine.start_session("sess3", "stu3", RECURSIVE_CODE, num_questions=2)
        q = engine.get_current_question("sess3")
        assert q is not None
        assert q.id == "q1"

    def test_get_current_question_unknown_session(self, engine):
        assert engine.get_current_question("no-such-session") is None

    @pytest.mark.asyncio
    async def test_submit_answer_returns_evaluation(self, engine):
        self._mock_groq(engine)
        engine.start_session("sess4", "stu4", RECURSIVE_CODE, num_questions=2)
        eval_ = await engine.submit_answer("sess4", "Factorial multiplies down to 1", 6.0)
        assert eval_.score == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_submit_answer_advances_question_index(self, engine):
        self._mock_groq(engine)
        engine.start_session("sess5", "stu5", RECURSIVE_CODE, num_questions=2)
        await engine.submit_answer("sess5", "recursion stops at base case", 4.0)
        session = engine.sessions["sess5"]
        assert session.current_question_index == 1

    @pytest.mark.asyncio
    async def test_get_verdict_pass(self, engine):
        self._mock_groq(engine, score=0.85)
        engine.start_session("sess6", "stu6", RECURSIVE_CODE, num_questions=2)
        session = engine.sessions["sess6"]
        # answer all questions
        for _ in session.questions:
            await engine.submit_answer("sess6", "good explanation", 5.0)
        verdict = engine.get_verdict("sess6")
        assert verdict["verdict"] == VivaVerdict.PASS.value
        assert verdict["average_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_get_verdict_fail(self, engine):
        self._mock_groq(engine, score=0.2)
        engine.start_session("sess7", "stu7", RECURSIVE_CODE, num_questions=2)
        session = engine.sessions["sess7"]
        for _ in session.questions:
            await engine.submit_answer("sess7", "I don't know", 2.0)
        verdict = engine.get_verdict("sess7")
        assert verdict["verdict"] == VivaVerdict.FAIL.value

    @pytest.mark.asyncio
    async def test_verdict_inconclusive_without_enough_answers(self, engine):
        engine.start_session("sess8", "stu8", RECURSIVE_CODE, num_questions=3)
        # submit only 1 answer (MIN_QUESTIONS = 2)
        self._mock_groq(engine, score=0.9)
        await engine.submit_answer("sess8", "some answer", 3.0)
        verdict = engine.get_verdict("sess8")
        assert verdict["verdict"] == VivaVerdict.INCONCLUSIVE.value

    def test_get_verdict_unknown_session(self, engine):
        result = engine.get_verdict("nope")
        assert "error" in result
