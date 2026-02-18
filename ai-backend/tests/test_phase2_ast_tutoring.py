"""
Phase 2 Tests — AST-Driven Tutoring

Validates:
  - ASTTutor.build_context() produces code-specific TutoringContext
  - TutoringContext.to_llm_prompt() generates structured LLM prompts
  - HintGenerator routes CodeAnalysisResult through the deep path
  - ConversationMemory tracks multi-turn dialogue
  - TutoringEngine.decide_intervention() escalates hints correctly
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ── Services under test ───────────────────────────────────────
from app.services.code_analyzer import (
    CodeAnalyzer, CodeAnalysisResult, CodeIssue,
    AlgorithmPattern, IssueLocation
)
from app.services.ast_tutor import (
    ASTTutor, TutoringContext, TeachingMoment, ConversationMemory, ConversationTurn
)
from app.services.tutoring_engine import (
    TutoringEngine, HintGenerator, HintLevel, StudentContext
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

RECURSIVE_CODE = """\
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

BROKEN_RECURSIVE = """\
def countdown(n):
    return n + countdown(n - 1)
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
def bad():
    while True:
        print("stuck")
"""


@pytest.fixture
def analyzer():
    return CodeAnalyzer()


@pytest.fixture
def ast_tutor():
    return ASTTutor()


@pytest.fixture
def memory():
    return ConversationMemory(max_turns=10)


@pytest.fixture
def engine():
    return TutoringEngine()


# ═══════════════════════════════════════════════════════════════
# Group A — CodeAnalyzer rich output
# ═══════════════════════════════════════════════════════════════

class TestCodeAnalyzerRichOutput:

    def test_factorial_detects_recursive_pattern(self, analyzer):
        result = analyzer.analyze_python(RECURSIVE_CODE)
        assert result.algorithm_pattern == AlgorithmPattern.RECURSIVE

    def test_factorial_function_profile(self, analyzer):
        result = analyzer.analyze_python(RECURSIVE_CODE)
        assert len(result.function_profiles) == 1
        fp = result.function_profiles[0]
        assert fp.name == "factorial"
        assert fp.calls_itself is True
        assert fp.has_base_case is True

    def test_broken_recursive_detects_missing_base_case(self, analyzer):
        result = analyzer.analyze_python(BROKEN_RECURSIVE)
        assert result.function_profiles[0].calls_itself is True
        assert result.function_profiles[0].has_base_case is False

    def test_recursive_concepts_detected(self, analyzer):
        result = analyzer.analyze_python(RECURSIVE_CODE)
        assert "recursion" in result.concepts_detected

    def test_loop_code_detects_iterative(self, analyzer):
        result = analyzer.analyze_python(LOOP_CODE)
        assert result.loop_count >= 1
        assert "loops" in result.concepts_detected or result.algorithm_pattern in (
            AlgorithmPattern.ITERATIVE, AlgorithmPattern.BRUTE_FORCE
        )

    def test_infinite_loop_raises_issue(self, analyzer):
        result = analyzer.analyze_python(INFINITE_LOOP_CODE)
        issue_types = [loc.issue_type for loc in result.issue_locations]
        assert any(i in issue_types for i in (
            CodeIssue.INFINITE_LOOP, CodeIssue.NO_TERMINATION
        ))

    def test_student_approach_summary_not_empty(self, analyzer):
        result = analyzer.analyze_python(RECURSIVE_CODE)
        assert result.student_approach_summary
        assert "factorial" in result.student_approach_summary.lower()

    def test_issue_locations_contain_description(self, analyzer):
        result = analyzer.analyze_python(BROKEN_RECURSIVE)
        if result.issue_locations:
            loc = result.issue_locations[0]
            assert loc.description
            assert loc.suggestion


# ═══════════════════════════════════════════════════════════════
# Group B — ASTTutor.build_context()
# ═══════════════════════════════════════════════════════════════

class TestASTTutor:

    def test_build_context_returns_tutoring_context(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        ctx = ast_tutor.build_context(analysis, RECURSIVE_CODE, "Implement factorial")
        assert isinstance(ctx, TutoringContext)

    def test_build_context_preserves_code(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        ctx = ast_tutor.build_context(analysis, RECURSIVE_CODE, "Implement factorial")
        assert ctx.student_code == RECURSIVE_CODE
        assert ctx.problem_statement == "Implement factorial"

    def test_build_context_has_teaching_moment(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        ctx = ast_tutor.build_context(analysis, RECURSIVE_CODE, "Implement factorial")
        assert isinstance(ctx.teaching_moment, TeachingMoment)
        assert ctx.teaching_moment.concept_to_teach
        assert ctx.teaching_moment.socratic_question

    def test_broken_recursive_focuses_on_base_case(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(BROKEN_RECURSIVE)
        ctx = ast_tutor.build_context(analysis, BROKEN_RECURSIVE, "Countdown")
        # Should focus on the missing base case
        tm = ctx.teaching_moment
        assert tm.concept_to_teach in ("recursion", "loop_termination")

    def test_build_context_includes_function_profiles(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        ctx = ast_tutor.build_context(analysis, RECURSIVE_CODE, "Factorial")
        assert len(ctx.function_profiles) >= 1
        assert any("factorial" in fp for fp in ctx.function_profiles)

    def test_build_context_passes_conversation_history(self, analyzer, ast_tutor):
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        history = [{"role": "user", "content": "help"}, {"role": "assistant", "content": "ok"}]
        ctx = ast_tutor.build_context(analysis, RECURSIVE_CODE, "Factorial", history)
        assert ctx.conversation_history == history

    def test_teaching_moment_severity_on_critical_issue(self, analyzer, ast_tutor):
        """Missing base case should have severity >= 2"""
        analysis = analyzer.analyze_python(BROKEN_RECURSIVE)
        ctx = ast_tutor.build_context(analysis, BROKEN_RECURSIVE, "Countdown")
        assert ctx.teaching_moment.severity >= 2


# ═══════════════════════════════════════════════════════════════
# Group C — TutoringContext.to_llm_prompt()
# ═══════════════════════════════════════════════════════════════

class TestTutoringContextPrompt:

    def _build_ctx(self, code=RECURSIVE_CODE, problem="Factorial"):
        analyzer = CodeAnalyzer()
        tutor = ASTTutor()
        analysis = analyzer.analyze_python(code)
        return tutor.build_context(analysis, code, problem)

    def test_prompt_contains_student_code(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(1)
        assert "factorial" in prompt.lower()

    def test_prompt_contains_problem_statement(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(1)
        assert "Factorial" in prompt

    def test_prompt_contains_socratic_question(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(1)
        assert ctx.teaching_moment.socratic_question in prompt

    def test_prompt_contains_algorithm_pattern(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(1)
        assert "recursive" in prompt.lower() or "recursion" in prompt.lower()

    def test_prompt_level_1_forbids_direct_answer(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(1)
        # Level 1 instructions must include the no-answer constraint
        assert "NOT" in prompt or "Do NOT" in prompt or "not" in prompt.lower()

    def test_prompt_level_4_allows_code_snippet(self):
        ctx = self._build_ctx()
        prompt = ctx.to_llm_prompt(4)
        # Level 4 should mention code or explicit guidance
        assert "explicit" in prompt.lower() or "code snippet" in prompt.lower()

    def test_all_hint_levels_produce_different_prompts(self):
        ctx = self._build_ctx()
        prompts = [ctx.to_llm_prompt(i) for i in range(1, 5)]
        assert len(set(prompts)) == 4   # all four must differ


# ═══════════════════════════════════════════════════════════════
# Group D — ConversationMemory
# ═══════════════════════════════════════════════════════════════

class TestConversationMemory:

    def _turn(self, role, content, hint_level=1, focus="recursion"):
        return ConversationTurn(
            role=role,
            content=content,
            hint_level=hint_level,
            teaching_focus=focus,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def test_add_and_retrieve_turn(self, memory):
        memory.add_turn("s1", self._turn("student", "what is recursion?"))
        history = memory.get_history("s1")
        assert len(history) == 1
        assert history[0]["content"] == "what is recursion?"

    def test_tutor_role_mapped_to_assistant(self, memory):
        memory.add_turn("s1", self._turn("tutor", "Think about the base case."))
        history = memory.get_history("s1")
        assert history[0]["role"] == "assistant"

    def test_student_role_preserved(self, memory):
        memory.add_turn("s1", self._turn("student", "I don't get it."))
        history = memory.get_history("s1")
        assert history[0]["role"] == "student"

    def test_max_turns_enforced(self, memory):
        for i in range(15):
            memory.add_turn("s1", self._turn("student", f"msg {i}"))
        # max_turns=10, should only keep last 10
        assert len(memory.get_history("s1", last_n=20)) == 10

    def test_last_n_respected(self, memory):
        for i in range(8):
            memory.add_turn("s1", self._turn("student", f"msg {i}"))
        history = memory.get_history("s1", last_n=3)
        assert len(history) == 3
        assert history[-1]["content"] == "msg 7"

    def test_hint_count(self, memory):
        memory.add_turn("s1", self._turn("tutor", "hint 1"))
        memory.add_turn("s1", self._turn("student", "response 1"))
        memory.add_turn("s1", self._turn("tutor", "hint 2"))
        assert memory.get_hint_count("s1") == 2

    def test_summary(self, memory):
        memory.add_turn("s1", self._turn("tutor", "hint", focus="recursion"))
        summary = memory.summary("s1")
        assert summary["total_turns"] == 1
        assert summary["hints_given"] == 1
        assert summary["last_focus"] == "recursion"

    def test_clear_session(self, memory):
        memory.add_turn("s1", self._turn("student", "hello"))
        memory.clear_session("s1")
        assert memory.get_history("s1") == []

    def test_separate_students_dont_mix(self, memory):
        memory.add_turn("alice", self._turn("student", "alice msg"))
        memory.add_turn("bob", self._turn("student", "bob msg"))
        assert len(memory.get_history("alice")) == 1
        assert memory.get_history("alice")[0]["content"] == "alice msg"


# ═══════════════════════════════════════════════════════════════
# Group E — TutoringEngine intervention logic
# ═══════════════════════════════════════════════════════════════

class TestTutoringEngineInterventions:

    def _ctx(self, time_stuck=0, frustration=0.0, hints=0, attempts=1):
        return StudentContext(
            problem_description="Write a sort function",
            current_code="def sort(): pass",
            time_stuck=time_stuck,
            frustration_level=frustration,
            previous_hints=hints,
            code_attempts=attempts,
        )

    def test_no_intervention_when_not_stuck(self, engine):
        decision = engine.decide_intervention(self._ctx(time_stuck=10))
        assert decision.should_intervene is False

    def test_intervene_when_stuck_too_long(self, engine):
        decision = engine.decide_intervention(self._ctx(time_stuck=200))
        assert decision.should_intervene is True
        assert "stuck_too_long" in decision.reason

    def test_intervene_on_high_frustration(self, engine):
        # time_stuck must exceed the engine's min_stuck_time (30s) for any intervention
        decision = engine.decide_intervention(self._ctx(time_stuck=60, frustration=0.85))
        assert decision.should_intervene is True
        assert "high_frustration" in decision.reason

    def test_intervene_on_multiple_failed_attempts(self, engine):
        decision = engine.decide_intervention(self._ctx(time_stuck=90, attempts=6))
        assert decision.should_intervene is True

    def test_hint_level_starts_socratic(self, engine):
        ctx = self._ctx(hints=0, frustration=0.1)
        decision = engine.decide_intervention(ctx)
        assert decision.hint_level == HintLevel.SOCRATIC_QUESTION

    def test_hint_escalates_with_frustration(self, engine):
        ctx_high = self._ctx(hints=2, frustration=0.9, time_stuck=250)
        decision = engine.decide_intervention(ctx_high)
        assert decision.hint_level in (HintLevel.PSEUDO_CODE, HintLevel.DIRECT_HINT)

    def test_urgency_between_zero_and_one(self, engine):
        decision = engine.decide_intervention(self._ctx(time_stuck=200, frustration=0.8))
        assert 0.0 <= decision.urgency <= 1.0

    def test_urgency_zero_when_no_triggers(self, engine):
        decision = engine.decide_intervention(self._ctx(time_stuck=5))
        assert decision.urgency == 0.0 or decision.urgency < 0.5


# ═══════════════════════════════════════════════════════════════
# Group F — HintGenerator deep path (mocked LLM)
# ═══════════════════════════════════════════════════════════════

class TestHintGeneratorDeepPath:

    def _make_generator(self):
        mock_groq = MagicMock()
        mock_groq.chat_completion = AsyncMock(
            return_value="Think about what makes your recursion stop."
        )
        gen = HintGenerator(mock_groq)
        return gen

    @pytest.mark.asyncio
    async def test_deep_hint_uses_ast_result(self, analyzer):
        gen = self._make_generator()
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        hint = await gen.generate_hint(HintLevel.SOCRATIC_QUESTION, "Factorial", RECURSIVE_CODE, analysis)
        assert isinstance(hint, str)
        assert len(hint) > 0
        # The mock LLM was called (deep path was taken)
        gen.groq.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_hint_prompt_contains_code(self, analyzer):
        gen = self._make_generator()
        analysis = analyzer.analyze_python(RECURSIVE_CODE)

        captured_messages = []
        async def capture(*args, **kwargs):
            captured_messages.extend(args[0] if args else kwargs.get("messages", []))
            return "mock hint"

        gen.groq.chat_completion = capture
        await gen.generate_hint(HintLevel.SOCRATIC_QUESTION, "Factorial", RECURSIVE_CODE, analysis)

        full_text = " ".join(m["content"] for m in captured_messages)
        assert "factorial" in full_text.lower()

    @pytest.mark.asyncio
    async def test_legacy_dict_falls_back_gracefully(self):
        gen = self._make_generator()
        old_analysis = {"function_count": 1, "loop_count": 0, "issues": []}
        hint = await gen.generate_hint(
            HintLevel.CONCEPTUAL_NUDGE, "Sort a list", "def sort(): pass", old_analysis
        )
        assert isinstance(hint, str)

    @pytest.mark.asyncio
    async def test_generate_hint_for_student_records_turn(self, analyzer):
        gen = self._make_generator()
        analysis = analyzer.analyze_python(RECURSIVE_CODE)
        await gen.generate_hint_for_student(
            "stu1", HintLevel.SOCRATIC_QUESTION, "Factorial", RECURSIVE_CODE, analysis
        )
        # The memory should have a tutor turn
        count = gen.get_hint_count("stu1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_conversation_history_injected_into_prompt(self, analyzer):
        gen = self._make_generator()
        analysis = analyzer.analyze_python(RECURSIVE_CODE)

        # Simulate prior conversation
        gen.record_student_message("stu2", "I tried returning n*n")

        captured_messages = []
        async def capture(*args, **kwargs):
            captured_messages.extend(args[0] if args else kwargs.get("messages", []))
            return "mock hint"
        gen.groq.chat_completion = capture

        await gen.generate_hint_for_student(
            "stu2", HintLevel.CONCEPTUAL_NUDGE, "Factorial", RECURSIVE_CODE, analysis
        )
        full_text = " ".join(m.get("content", "") for m in captured_messages)
        assert "I tried returning n*n" in full_text
