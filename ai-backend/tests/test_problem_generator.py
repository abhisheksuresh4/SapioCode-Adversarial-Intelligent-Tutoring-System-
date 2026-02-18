"""Comprehensive Test Suite for Problem Generator (mocked — no live API calls)"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.problem_generator import (
    ProblemGenerator,
    ProblemSpecification,
    ProblemTestCase,
    TestCase,
)


# ── helpers ──────────────────────────────────────────────────────────

def _make_spec_json(
    title="Test Problem",
    description="Write a function that does X.",
    difficulty="easy",
    concepts=None,
    starter_code="def solve(x):\n    pass",
    solution_template="Step 1: ...",
    test_cases=None,
    hints=None,
):
    """Build a valid JSON spec string the parser expects."""
    concepts = concepts or ["loops"]
    hints = hints or [
        "What data structure holds items in order?",
        "Think about iterating once through the list.",
        "Consider using a for-loop with a running max.",
    ]
    test_cases = test_cases or [
        {"input": "1", "expected_output": "1", "explanation": "single", "is_hidden": False},
        {"input": "2", "expected_output": "4", "explanation": "square", "is_hidden": False},
        {"input": "0", "expected_output": "0", "explanation": "zero", "is_hidden": True},
    ]
    return json.dumps({
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "concepts": concepts,
        "starter_code": starter_code,
        "solution_template": solution_template,
        "test_cases": test_cases,
        "hints": hints,
    })


def _make_additional_tc_json(n=2):
    """Build a JSON array of additional test-case dicts."""
    return json.dumps([
        {"input": f"edge_{i}", "expected_output": f"out_{i}",
         "explanation": f"edge case {i}", "is_hidden": True}
        for i in range(n)
    ])


def _make_refine_json(description="Harder version.", difficulty="hard"):
    return json.dumps({
        "description": description,
        "difficulty": difficulty,
        "suggested_changes": "Increased constraint sizes.",
    })


def _generator_with_mock():
    """Return a ProblemGenerator whose groq_service is fully mocked."""
    gen = ProblemGenerator.__new__(ProblemGenerator)
    gen.supported_languages = ["python", "javascript", "java", "cpp"]
    mock_groq = MagicMock()
    mock_groq.generate_structured_response = AsyncMock()
    gen.groq_service = mock_groq
    return gen, mock_groq


# ── TestCase / ProblemTestCase alias ────────────────────────────────

class TestDataclassAlias:
    def test_alias_identity(self):
        assert TestCase is ProblemTestCase

    def test_dataclass_fields(self):
        tc = ProblemTestCase(input="1", expected_output="2",
                             explanation="check", is_hidden=False)
        assert tc.input == "1"
        assert tc.expected_output == "2"
        assert tc.is_hidden is False


# ── Basic generation ────────────────────────────────────────────────

class TestProblemGeneratorBasics:
    @pytest.mark.asyncio
    async def test_generate_easy_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            difficulty="easy",
            concepts=["basic math"],
            test_cases=[
                {"input": "2", "expected_output": "True", "explanation": "even", "is_hidden": False},
                {"input": "3", "expected_output": "False", "explanation": "odd", "is_hidden": False},
                {"input": "0", "expected_output": "True", "explanation": "zero", "is_hidden": True},
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Write a function to check if a number is even",
            language="python", difficulty="easy", num_test_cases=3,
        )
        assert spec is not None
        assert spec.title
        assert spec.description
        assert spec.difficulty == "easy"
        assert len(spec.test_cases) == 3
        assert spec.starter_code
        assert len(spec.hints) >= 2
        assert spec.concepts

    @pytest.mark.asyncio
    async def test_generate_medium_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            difficulty="medium",
            concepts=["recursion", "fibonacci"],
            test_cases=[
                {"input": str(i), "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": False}
                for i in range(5)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Write a function to find the nth Fibonacci number using recursion",
            language="python", difficulty="medium", num_test_cases=5,
        )
        assert spec.difficulty == "medium"
        assert len(spec.test_cases) == 5
        assert any("recursion" in c.lower() or "fibonacci" in c.lower() for c in spec.concepts)

    @pytest.mark.asyncio
    async def test_generate_hard_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            difficulty="hard",
            concepts=["dynamic programming", "subsequences"],
            test_cases=[
                {"input": str(i), "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": i > 2}
                for i in range(5)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Implement a function to find the longest increasing subsequence",
            language="python", difficulty="hard", num_test_cases=5,
        )
        assert spec.difficulty == "hard"
        assert len(spec.test_cases) >= 5


# ── Component validation ────────────────────────────────────────────

class TestProblemComponentsValidation:
    @pytest.mark.asyncio
    async def test_starter_code_format(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            starter_code="def reverse_string(s: str) -> str:\n    # Your code here\n    pass",
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Write a function to reverse a string",
            language="python", difficulty="easy", num_test_cases=3,
        )
        assert "def" in spec.starter_code
        assert ":" in spec.starter_code

    @pytest.mark.asyncio
    async def test_test_cases_structure(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            test_cases=[
                {"input": "[1,2,3]", "expected_output": "3", "explanation": "max of list", "is_hidden": False},
                {"input": "[5]", "expected_output": "5", "explanation": "single", "is_hidden": False},
                {"input": "[-1,-2]", "expected_output": "-1", "explanation": "negatives", "is_hidden": True},
                {"input": "[0]", "expected_output": "0", "explanation": "zero", "is_hidden": False},
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Find the maximum element in a list",
            language="python", difficulty="easy", num_test_cases=4,
        )
        for tc in spec.test_cases:
            assert tc.input
            assert tc.expected_output
            assert tc.explanation
            assert isinstance(tc.is_hidden, bool)

    @pytest.mark.asyncio
    async def test_hints_progression(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            hints=[
                "What does it mean for a word to read the same forwards and backwards?",
                "Consider comparing characters from the outside in.",
                "Use two pointers or reverse the string and compare.",
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Check if a string is a palindrome",
            language="python", difficulty="easy", num_test_cases=3,
        )
        assert len(spec.hints) >= 2
        assert "?" in spec.hints[0] or len(spec.hints[0]) < len(spec.hints[-1])


# ── Language support ────────────────────────────────────────────────

class TestMultipleLanguages:
    @pytest.mark.asyncio
    async def test_python_generation(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            starter_code="def sum_list(nums):\n    pass",
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Sum all elements in a list",
            language="python", difficulty="easy", num_test_cases=3,
        )
        assert "def" in spec.starter_code

    @pytest.mark.asyncio
    async def test_unsupported_language(self):
        gen, _ = _generator_with_mock()
        with pytest.raises(ValueError):
            await gen.generate_problem_from_text(
                raw_description="Test problem",
                language="cobol", difficulty="easy", num_test_cases=3,
            )


# ── Additional test-case generation ────────────────────────────────

class TestAdditionalTestCases:
    @pytest.mark.asyncio
    async def test_generate_additional_cases(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.side_effect = [
            _make_spec_json(
                test_cases=[
                    {"input": "5", "expected_output": "120", "explanation": "5!", "is_hidden": False},
                    {"input": "0", "expected_output": "1", "explanation": "0!", "is_hidden": False},
                    {"input": "1", "expected_output": "1", "explanation": "1!", "is_hidden": True},
                ],
            ),
            _make_additional_tc_json(2),
        ]
        spec = await gen.generate_problem_from_text(
            raw_description="Calculate factorial",
            language="python", difficulty="easy", num_test_cases=3,
        )
        new_cases = await gen.generate_additional_test_cases(
            problem_description=spec.description,
            existing_test_cases=spec.test_cases,
            num_additional=2,
        )
        assert len(new_cases) == 2
        for tc in new_cases:
            assert tc.is_hidden is True
            assert tc.input
            assert tc.expected_output


# ── Domain-specific problems ────────────────────────────────────────

class TestDomainSpecificProblems:
    @pytest.mark.asyncio
    async def test_array_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            concepts=["arrays", "iteration"],
            test_cases=[
                {"input": f"[{i}]", "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": False}
                for i in range(4)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Find the second largest element in an array",
            language="python", difficulty="easy", num_test_cases=4,
        )
        assert any("array" in c.lower() or "list" in c.lower() for c in spec.concepts)

    @pytest.mark.asyncio
    async def test_string_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            concepts=["string", "iteration"],
            test_cases=[
                {"input": f"s{i}", "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": False}
                for i in range(4)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Count the number of vowels in a string",
            language="python", difficulty="easy", num_test_cases=4,
        )
        assert any("string" in c.lower() for c in spec.concepts)

    @pytest.mark.asyncio
    async def test_recursion_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            difficulty="medium",
            concepts=["recursion", "math"],
            test_cases=[
                {"input": str(i), "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": False}
                for i in range(4)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Calculate the factorial using recursion",
            language="python", difficulty="medium", num_test_cases=4,
        )
        assert any("recursion" in c.lower() for c in spec.concepts)

    @pytest.mark.asyncio
    async def test_sorting_problem(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            difficulty="medium",
            concepts=["sorting", "algorithms"],
            test_cases=[
                {"input": str(i), "expected_output": str(i), "explanation": f"tc{i}", "is_hidden": False}
                for i in range(4)
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Implement bubble sort algorithm",
            language="python", difficulty="medium", num_test_cases=4,
        )
        assert any("sort" in c.lower() for c in spec.concepts)


# ── Edge cases ──────────────────────────────────────────────────────

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_description(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(title="Empty Problem")
        spec = await gen.generate_problem_from_text(
            raw_description="", language="python", difficulty="easy", num_test_cases=3,
        )
        assert spec.title or spec.description

    @pytest.mark.asyncio
    async def test_minimum_test_cases(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_spec_json(
            test_cases=[
                {"input": "1+1", "expected_output": "2", "explanation": "add", "is_hidden": False},
                {"input": "0+0", "expected_output": "0", "explanation": "zero", "is_hidden": False},
                {"input": "-1+1", "expected_output": "0", "explanation": "neg", "is_hidden": True},
            ],
        )
        spec = await gen.generate_problem_from_text(
            raw_description="Add two numbers", language="python", difficulty="easy", num_test_cases=3,
        )
        assert len(spec.test_cases) >= 3

    @pytest.mark.asyncio
    async def test_parse_error_raises(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = "NOT VALID JSON {{{{"
        with pytest.raises(ValueError, match="Failed to parse"):
            await gen.generate_problem_from_text(
                raw_description="anything", language="python", difficulty="easy", num_test_cases=3,
            )


# ── Difficulty refinement ──────────────────────────────────────────

class TestDifficultyRefinement:
    @pytest.mark.asyncio
    async def test_refine_to_harder(self):
        gen, mock = _generator_with_mock()
        mock.generate_structured_response.return_value = _make_refine_json(
            description="Harder version of the problem.", difficulty="hard",
        )
        original = ProblemSpecification(
            title="Sum", description="Sum list.", difficulty="easy",
            concepts=["loops"], starter_code="def s(l): pass",
            solution_template="iterate", test_cases=[], hints=["h1"],
        )
        refined = await gen.refine_problem_difficulty(original, "harder")
        assert refined.difficulty == "hard"
        assert "Harder" in refined.description


# ── Prompt construction ────────────────────────────────────────────

class TestPromptBuilding:
    def test_build_specification_prompt_contains_description(self):
        gen, _ = _generator_with_mock()
        prompt = gen._build_specification_prompt("reverse a string", "python", "easy", 3)
        assert "reverse a string" in prompt
        assert "python" in prompt.lower()
        assert "easy" in prompt.lower()

    def test_build_specification_prompt_requests_json(self):
        gen, _ = _generator_with_mock()
        prompt = gen._build_specification_prompt("sort a list", "python", "medium", 5)
        assert "JSON" in prompt or "json" in prompt


# ── Integration: complete flow ──────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_problem_creation_flow():
    gen, mock = _generator_with_mock()
    mock.generate_structured_response.side_effect = [
        _make_spec_json(
            title="Anagram Checker",
            concepts=["strings", "sorting"],
            test_cases=[
                {"input": f"pair_{i}", "expected_output": str(i % 2 == 0),
                 "explanation": f"tc{i}", "is_hidden": False}
                for i in range(4)
            ],
        ),
        _make_additional_tc_json(2),
    ]

    spec = await gen.generate_problem_from_text(
        raw_description="Check if two strings are anagrams",
        language="python", difficulty="medium", num_test_cases=4,
    )
    assert spec.title
    assert len(spec.test_cases) == 4

    additional = await gen.generate_additional_test_cases(
        problem_description=spec.description,
        existing_test_cases=spec.test_cases,
        num_additional=2,
    )
    assert len(additional) == 2
    assert len(spec.test_cases) + len(additional) == 6


if __name__ == "__main__":
    print("🧪 Running Problem Generator Test Suite...")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])
