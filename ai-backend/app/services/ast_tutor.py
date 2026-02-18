"""
AST Tutor Service
=================
The "Neuro-Symbolic" bridge — takes deep AST results and produces
a structured *tutoring context* that makes LLM hints CODE-SPECIFIC.

Instead of generic hints like "check your loop termination", the tutor
produces references like:
  "Your `while lo <= hi` loop on line 8 increments `lo`... what happens
   when `nums` is empty?"

This file is PURE Python (no async, no Groq calls).
It is used by HintGenerator to enrich the LLM prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from app.services.code_analyzer import (
    CodeAnalysisResult,
    AlgorithmPattern,
    CodeIssue,
    IssueLocation,
    FunctionProfile,
)


# ══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════

@dataclass
class TeachingMoment:
    """
    The single most important thing to teach right now.
    ASTTutor picks ONE even if there are multiple issues.
    """
    focus_type: str           # "missing_base_case" | "infinite_loop" | "algorithm_choice" | ...
    headline: str             # Short summary for the system log
    line: Optional[int]       # Specific line to reference (or None)
    code_snippet: str         # Exact snippet from student's code
    socratic_question: str    # What to ASK (not tell) the student
    concept_to_teach: str     # Curriculum concept this maps to
    severity: int             # 1 = mild, 3 = critical


@dataclass
class TutoringContext:
    """
    Structured context injected into the LLM prompt.
    Contains EVERYTHING the LLM needs to generate a code-specific hint.
    """
    student_code: str
    problem_statement: str

    # Primary focus
    teaching_moment: TeachingMoment

    # Supporting context
    algorithm_pattern: str            # e.g. "recursive", "two_pointer"
    approach_summary: str             # Plain-English summary of their code
    function_profiles: List[str]      # Human-readable fn descriptions
    data_structures: List[str]
    concepts: List[str]
    all_issues: List[str]             # All detected issues (not just focus)

    # Conversation memory
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    def to_llm_prompt(self, hint_level: int) -> str:
        """
        Build a complete, rich prompt for the LLM.
        `hint_level` controls how much to reveal (1=Socratic, 4=Direct).
        """
        lines = []

        # ── Preamble ──────────────────────────────────────
        lines.append(f"PROBLEM:\n{self.problem_statement}\n")

        # ── Student's code ────────────────────────────────
        lines.append(f"STUDENT'S CODE:\n```python\n{self.student_code}\n```\n")

        # ── Symbolic analysis ─────────────────────────────
        lines.append("SYMBOLIC CODE ANALYSIS (from AST):")
        lines.append(f"  Approach : {self.algorithm_pattern.replace('_', ' ')}")
        lines.append(f"  Summary  : {self.approach_summary}")
        if self.function_profiles:
            lines.append("  Functions:")
            for f in self.function_profiles:
                lines.append(f"    {f}")
        if self.data_structures:
            lines.append(f"  Data structures : {', '.join(self.data_structures)}")
        if self.all_issues:
            lines.append(f"  Detected issues : {', '.join(self.all_issues)}")
        lines.append("")

        # ── Teaching focus ────────────────────────────────
        tm = self.teaching_moment
        lines.append("TUTORING FOCUS (most important issue right now):")
        lines.append(f"  Type    : {tm.focus_type}")
        lines.append(f"  Concept : {tm.concept_to_teach}")
        if tm.line:
            lines.append(f"  Line    : {tm.line}  →  `{tm.code_snippet.strip()}`")
        else:
            lines.append(f"  Code    : `{tm.code_snippet.strip()}`")
        lines.append(f"  Question to explore: {tm.socratic_question}")
        lines.append("")

        # ── Hint level instructions ───────────────────────
        level_instructions = {
            1: (
                "Ask ONE Socratic question referencing the specific code element above. "
                "Do NOT reveal the answer. Do NOT show code. "
                "Mention the actual function name, variable, or line from their code."
            ),
            2: (
                "Point the student toward the concept they need. "
                "Reference the specific line/function. You may give a general example "
                "of the concept (unrelated to their problem) but NOT their solution."
            ),
            3: (
                "Give algorithmic guidance using pseudo-code. "
                "Reference their actual function names and variables. "
                "Show the STRUCTURE but leave the implementation to them."
            ),
            4: (
                "Provide explicit guidance. You may show a code snippet but leave "
                "key parts blank (e.g., `____`) for the student to fill in. "
                "Always reference their actual code."
            ),
        }
        lines.append(f"YOUR TASK (hint level {hint_level}/4):")
        lines.append(level_instructions.get(hint_level, level_instructions[1]))

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# AST TUTOR
# ══════════════════════════════════════════════════════════════

class ASTTutor:
    """
    Converts a deep CodeAnalysisResult → TutoringContext.

    This is the symbolic half of the Neuro-Symbolic system:
    it figures out WHAT to teach and WHERE to focus, then
    the LLM (neural half) figures out HOW to say it.
    """

    # Ordering of issue severity (higher index = more critical)
    ISSUE_PRIORITY = [
        CodeIssue.SYNTAX_ERROR,
        CodeIssue.MISSING_RETURN,
        CodeIssue.MISSING_BASE_CASE,
        CodeIssue.NO_TERMINATION,
        CodeIssue.OFF_BY_ONE,
        CodeIssue.WRONG_ALGORITHM,
        CodeIssue.WRONG_RETURN_TYPE,
        CodeIssue.INEFFICIENT_SOLUTION,
        CodeIssue.SHADOWED_VARIABLE,
    ]

    def build_context(
        self,
        analysis: CodeAnalysisResult,
        student_code: str,
        problem_statement: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> TutoringContext:
        """
        Main entry point. Takes a CodeAnalysisResult and returns
        a fully structured TutoringContext ready for LLM injection.
        """
        tm = self._pick_teaching_moment(analysis, student_code)
        fn_descriptions = self._describe_functions(analysis.function_profiles)
        issue_names = [loc.issue_type.value.replace("_", " ")
                       for loc in analysis.issue_locations]

        return TutoringContext(
            student_code=student_code,
            problem_statement=problem_statement,
            teaching_moment=tm,
            algorithm_pattern=analysis.algorithm_pattern.value,
            approach_summary=analysis.student_approach_summary or "No summary available",
            function_profiles=fn_descriptions,
            data_structures=analysis.data_structures_used,
            concepts=analysis.concepts_detected,
            all_issues=issue_names,
            conversation_history=conversation_history or [],
        )

    # ── Private: pick the single most important teaching moment ──

    def _pick_teaching_moment(
        self, analysis: CodeAnalysisResult, code: str
    ) -> TeachingMoment:
        """
        Choose the ONE issue the tutor should focus on.
        Priority: most severe structural issue → algorithm choice → generic.
        """
        # If there are located issues, pick highest priority
        if analysis.issue_locations:
            best = self._highest_priority_issue(analysis.issue_locations)
            return TeachingMoment(
                focus_type=best.issue_type.value,
                headline=best.description,
                line=best.line,
                code_snippet=best.code_snippet,
                socratic_question=best.suggestion,
                concept_to_teach=self._issue_to_concept(best.issue_type),
                severity=self._issue_severity(best.issue_type),
            )

        # No located issues → focus on algorithm pattern
        return self._pattern_moment(analysis, code)

    def _highest_priority_issue(
        self, locations: List[IssueLocation]
    ) -> IssueLocation:
        """Return the highest-priority issue from the list."""
        def priority(loc: IssueLocation) -> int:
            try:
                return self.ISSUE_PRIORITY.index(loc.issue_type)
            except ValueError:
                return -1

        return max(locations, key=priority)

    def _pattern_moment(
        self, analysis: CodeAnalysisResult, code: str
    ) -> TeachingMoment:
        """
        When there are no structural issues, focus on algorithmic quality.
        E.g. using brute force when two-pointer would work.
        """
        pattern = analysis.algorithm_pattern
        lines = code.split("\n")
        snippet = lines[0].strip() if lines else code[:60]

        suggestions: Dict[AlgorithmPattern, Tuple[str, str, str]] = {
            AlgorithmPattern.BRUTE_FORCE: (
                "algorithm_efficiency",
                "Your nested loops give O(n²). Could a linear scan work?",
                "time_complexity",
            ),
            AlgorithmPattern.RECURSIVE: (
                "recursion_correctness",
                "What input makes your function stop calling itself?",
                "recursion",
            ),
            AlgorithmPattern.DYNAMIC_PROG: (
                "dp_subproblem",
                "What is the smallest sub-problem that this reduces to?",
                "dynamic_programming",
            ),
            AlgorithmPattern.TWO_POINTER: (
                "two_pointer_invariant",
                "What property of your left/right pointers must always hold?",
                "two_pointers",
            ),
        }

        focus_type, question, concept = suggestions.get(
            pattern,
            (
                "general_approach",
                "Walk me through what your code does on a small example.",
                "problem_solving",
            ),
        )

        return TeachingMoment(
            focus_type=focus_type,
            headline=f"Using {pattern.value} approach — checking correctness",
            line=None,
            code_snippet=snippet,
            socratic_question=question,
            concept_to_teach=concept,
            severity=1,
        )

    # ── Private: helpers ─────────────────────────────────────

    def _describe_functions(self, profiles: List[FunctionProfile]) -> List[str]:
        """Produce human-readable one-liners for each function profile."""
        result = []
        for fp in profiles:
            parts = [f"`{fp.name}({', '.join(fp.param_names)})`"]
            if fp.calls_itself:
                parts.append("recursive")
                if not fp.has_base_case:
                    parts.append("⚠ no base case")
            if not fp.has_return:
                parts.append("⚠ no return")
            if fp.loop_count:
                parts.append(f"{fp.loop_count} loop(s)")
            result.append(" — ".join(parts))
        return result

    def _issue_to_concept(self, issue: CodeIssue) -> str:
        mapping = {
            CodeIssue.SYNTAX_ERROR:      "syntax",
            CodeIssue.INFINITE_LOOP:     "loop_termination",
            CodeIssue.NO_TERMINATION:    "loop_termination",
            CodeIssue.MISSING_RETURN:    "functions",
            CodeIssue.MISSING_BASE_CASE: "recursion",
            CodeIssue.OFF_BY_ONE:        "boundary_conditions",
            CodeIssue.WRONG_ALGORITHM:   "algorithm_design",
            CodeIssue.WRONG_RETURN_TYPE: "type_correctness",
            CodeIssue.INEFFICIENT_SOLUTION: "time_complexity",
            CodeIssue.SHADOWED_VARIABLE: "variable_scoping",
            CodeIssue.EMPTY_FUNCTION:    "functions",
        }
        return mapping.get(issue, "problem_solving")

    def _issue_severity(self, issue: CodeIssue) -> int:
        critical = {CodeIssue.SYNTAX_ERROR, CodeIssue.INFINITE_LOOP,
                    CodeIssue.NO_TERMINATION, CodeIssue.MISSING_BASE_CASE}
        medium   = {CodeIssue.MISSING_RETURN, CodeIssue.OFF_BY_ONE,
                    CodeIssue.WRONG_ALGORITHM, CodeIssue.WRONG_RETURN_TYPE}
        if issue in critical: return 3
        if issue in medium:   return 2
        return 1


# ══════════════════════════════════════════════════════════════
# CONVERSATION MEMORY
# ══════════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """One exchange in the tutoring dialogue."""
    role: str        # "student" | "tutor"
    content: str
    hint_level: int  # 1-4
    teaching_focus: str
    timestamp: str   # ISO string


class ConversationMemory:
    """
    Per-student conversation history for multi-turn Socratic dialogue.
    Stored in-process (no DB required); IntegrationBridge owns one instance.
    """

    def __init__(self, max_turns: int = 20):
        self._sessions: Dict[str, List[ConversationTurn]] = {}
        self.max_turns = max_turns

    def add_turn(self, student_id: str, turn: ConversationTurn) -> None:
        if student_id not in self._sessions:
            self._sessions[student_id] = []
        self._sessions[student_id].append(turn)
        # Keep only recent context
        if len(self._sessions[student_id]) > self.max_turns:
            self._sessions[student_id] = self._sessions[student_id][-self.max_turns:]

    def get_history(
        self, student_id: str, last_n: int = 6
    ) -> List[Dict[str, str]]:
        """
        Return last N turns as OpenAI-style message dicts
        so they can be passed directly to the LLM.
        """
        turns = self._sessions.get(student_id, [])[-last_n:]
        return [{"role": t.role if t.role != "tutor" else "assistant",
                 "content": t.content}
                for t in turns]

    def get_hint_count(self, student_id: str) -> int:
        turns = self._sessions.get(student_id, [])
        return sum(1 for t in turns if t.role == "tutor")

    def clear_session(self, student_id: str) -> None:
        self._sessions.pop(student_id, None)

    def summary(self, student_id: str) -> Dict[str, Any]:
        turns = self._sessions.get(student_id, [])
        return {
            "total_turns": len(turns),
            "hints_given": sum(1 for t in turns if t.role == "tutor"),
            "last_focus": turns[-1].teaching_focus if turns else None,
        }
