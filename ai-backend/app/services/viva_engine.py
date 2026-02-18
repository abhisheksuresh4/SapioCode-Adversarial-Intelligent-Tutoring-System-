"""
Viva Voce Engine for SapioCode

This module implements the oral examination (Viva) system that verifies
student understanding of their submitted code.

Components:
1. QuestionGenerator - Creates targeted questions about specific code elements
2. SemanticVerifier - Compares student's verbal explanation to code logic
3. VivaSession - Manages the complete Viva examination flow

Why Viva Voce?
- Detects if student actually wrote/understood their code
- Prevents copy-paste submissions
- Tests deeper understanding beyond syntax
- Socratic approach: asks about specific lines/functions
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import random
from datetime import datetime

from app.services.code_analyzer import CodeAnalyzer, CodeAnalysisResult
from app.services.groq_service import GroqService


class VivaVerdict(Enum):
    """Final verdict of Viva examination"""
    PASS = "pass"                       # Student clearly understands
    WEAK_UNDERSTANDING = "weak"         # Partial understanding
    FAIL = "fail"                       # Cannot explain their code
    INCONCLUSIVE = "inconclusive"       # Need more questions


class QuestionType(Enum):
    """Types of Viva questions"""
    FUNCTION_PURPOSE = "function_purpose"    # "What does this function do?"
    LINE_EXPLANATION = "line_explanation"    # "Explain what happens on line X"
    LOGIC_FLOW = "logic_flow"                # "Walk me through the logic"
    VARIABLE_ROLE = "variable_role"          # "What is this variable for?"
    EDGE_CASE = "edge_case"                  # "What happens if input is X?"
    WHY_CHOICE = "why_choice"                # "Why did you use X instead of Y?"


@dataclass
class VivaQuestion:
    """A single Viva question"""
    id: str
    question_type: QuestionType
    question_text: str
    target_code: str           # The specific code this question is about
    target_line: Optional[int] # Line number if applicable
    expected_concepts: List[str]  # Key concepts answer should contain
    difficulty: int = 1        # 1-3 (easy to hard)


@dataclass
class StudentAnswer:
    """Student's answer to a Viva question"""
    question_id: str
    transcribed_text: str
    audio_duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AnswerEvaluation:
    """Evaluation of a single answer"""
    question_id: str
    score: float              # 0.0 to 1.0
    matched_concepts: List[str]
    missing_concepts: List[str]
    feedback: str
    is_acceptable: bool       # Score >= 0.5


@dataclass
class VivaSession:
    """Complete Viva examination session"""
    session_id: str
    student_id: str
    code: str
    analysis: CodeAnalysisResult
    questions: List[VivaQuestion] = field(default_factory=list)
    answers: List[StudentAnswer] = field(default_factory=list)
    evaluations: List[AnswerEvaluation] = field(default_factory=list)
    current_question_index: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    verdict: Optional[VivaVerdict] = None


class QuestionGenerator:
    """
    Generates targeted Viva questions based on code analysis.
    
    Strategy:
    1. Analyze code structure (functions, loops, variables)
    2. Identify key logic points
    3. Generate questions from easiest to hardest
    4. Focus on areas where plagiarism is common
    """
    
    # Question templates by type
    TEMPLATES = {
        QuestionType.FUNCTION_PURPOSE: [
            "Can you explain what the function '{name}' does?",
            "What is the purpose of your '{name}' function?",
            "Walk me through what '{name}' accomplishes.",
        ],
        QuestionType.LINE_EXPLANATION: [
            "Looking at line {line}, can you explain what this code does?",
            "What happens when line {line} executes?",
            "Explain the logic on line {line} of your code.",
        ],
        QuestionType.LOGIC_FLOW: [
            "Can you trace through your code with an input of {example}?",
            "Walk me through how your program handles {scenario}.",
            "Explain the step-by-step execution of your main logic.",
        ],
        QuestionType.VARIABLE_ROLE: [
            "What is the purpose of the variable '{name}'?",
            "Why do you need the variable '{name}' in your solution?",
            "Explain what '{name}' stores and how it changes.",
        ],
        QuestionType.EDGE_CASE: [
            "What happens if the input is empty?",
            "How does your code handle negative numbers?",
            "What if someone passes None to your function?",
        ],
        QuestionType.WHY_CHOICE: [
            "Why did you choose to use a {construct} here?",
            "What made you decide on this approach over alternatives?",
            "Could you have solved this differently? Why this way?",
        ],
    }
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
    
    def generate_questions(
        self,
        code: str,
        analysis: CodeAnalysisResult,
        num_questions: int = 3
    ) -> List[VivaQuestion]:
        """
        Generate Viva questions based on AST analysis.

        Phase 3 upgrade: uses FunctionProfile (recursion, base case, loops,
        param names), algorithm_pattern, concepts_detected and issue_locations
        from the rich CodeAnalysisResult so every question is code-specific.
        """
        questions = []
        code_lines = code.split("\n")

        # ── Priority 1: Function-level questions (deep profile aware) ──
        if hasattr(analysis, 'function_profiles') and analysis.function_profiles:
            for fp in analysis.function_profiles[:2]:
                q = self._create_function_question_from_profile(fp, code)
                if q:
                    questions.append(q)
        else:
            # Legacy fallback — code_structure dict
            functions = analysis.code_structure.get("functions", [])
            for func_name in functions[:2]:
                q = self._create_function_question(func_name, code)
                if q:
                    questions.append(q)

        # ── Priority 2: Algorithm-pattern question ─────────────────────
        if hasattr(analysis, 'algorithm_pattern') and analysis.algorithm_pattern:
            q = self._create_algorithm_pattern_question(analysis, code)
            if q:
                questions.append(q)

        # ── Priority 3: Issue-focused question (if any issues detected) ─
        if hasattr(analysis, 'issue_locations') and analysis.issue_locations:
            q = self._create_issue_question(analysis.issue_locations[0], code_lines)
            if q:
                questions.append(q)
        elif analysis.loop_count > 0:
            q = self._create_loop_question(code_lines, analysis)
            if q:
                questions.append(q)

        # ── Priority 4: Variable / edge-case questions ─────────────────
        variables = self._extract_variables(code)
        for var in variables[:1]:
            q = self._create_variable_question(var, code)
            if q:
                questions.append(q)

        q = self._create_edge_case_question(code, analysis)
        if q:
            questions.append(q)

        # Shuffle, limit, assign IDs
        random.shuffle(questions)
        questions = questions[:num_questions]
        for i, q in enumerate(questions):
            q.id = f"q{i+1}"

        return questions
    
    def _create_function_question(self, func_name: str, code: str) -> Optional[VivaQuestion]:
        """Create a question about a specific function"""
        template = random.choice(self.TEMPLATES[QuestionType.FUNCTION_PURPOSE])
        
        # Find function code
        func_code = self._extract_function_code(code, func_name)
        
        return VivaQuestion(
            id="",
            question_type=QuestionType.FUNCTION_PURPOSE,
            question_text=template.format(name=func_name),
            target_code=func_code or f"def {func_name}(...)",
            target_line=None,
            expected_concepts=self._infer_function_concepts(func_name, func_code),
            difficulty=1
        )
    
    def _create_loop_question(self, code_lines: List[str], analysis: CodeAnalysisResult) -> Optional[VivaQuestion]:
        """Create a question about loop logic"""
        # Find first loop line
        for i, line in enumerate(code_lines, 1):
            stripped = line.strip()
            if stripped.startswith(("for ", "while ")):
                template = random.choice(self.TEMPLATES[QuestionType.LINE_EXPLANATION])
                return VivaQuestion(
                    id="",
                    question_type=QuestionType.LINE_EXPLANATION,
                    question_text=template.format(line=i),
                    target_code=line.strip(),
                    target_line=i,
                    expected_concepts=["iteration", "loop", "condition"],
                    difficulty=2
                )
        return None
    
    def _create_variable_question(self, var_name: str, code: str) -> Optional[VivaQuestion]:
        """Create a question about a variable's purpose"""
        template = random.choice(self.TEMPLATES[QuestionType.VARIABLE_ROLE])
        
        return VivaQuestion(
            id="",
            question_type=QuestionType.VARIABLE_ROLE,
            question_text=template.format(name=var_name),
            target_code=f"{var_name} = ...",
            target_line=None,
            expected_concepts=["purpose", "stores", "value", "type"],
            difficulty=1
        )
    
    def _create_edge_case_question(self, code: str, analysis: CodeAnalysisResult) -> Optional[VivaQuestion]:
        """Create an edge case question"""
        template = random.choice(self.TEMPLATES[QuestionType.EDGE_CASE])
        
        return VivaQuestion(
            id="",
            question_type=QuestionType.EDGE_CASE,
            question_text=template,
            target_code="",
            target_line=None,
            expected_concepts=["edge case", "error", "handle", "check"],
            difficulty=3
        )
    
    def _extract_function_code(self, code: str, func_name: str) -> Optional[str]:
        """Extract the code of a specific function"""
        lines = code.split("\n")
        in_function = False
        func_lines = []
        indent_level = 0
        
        for line in lines:
            if f"def {func_name}" in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                func_lines.append(line)
            elif in_function:
                if line.strip() == "":
                    func_lines.append(line)
                elif len(line) - len(line.lstrip()) > indent_level:
                    func_lines.append(line)
                else:
                    break
        
        return "\n".join(func_lines) if func_lines else None
    
    def _extract_variables(self, code: str) -> List[str]:
        """Extract significant variable names from code"""
        import re
        # Match variable assignments (simple pattern)
        pattern = r'^(\s*)([a-z_][a-z0-9_]*)\s*='
        variables = []
        
        for line in code.split("\n"):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                var_name = match.group(2)
                # Skip common loop variables and builtins
                if var_name not in ['i', 'j', 'k', 'x', 'y', '_', 'self']:
                    variables.append(var_name)
        
        return list(set(variables))
    
    def _infer_function_concepts(self, func_name: str, func_code: Optional[str]) -> List[str]:
        """Infer expected concepts from function name and code"""
        concepts = ["purpose", "input", "output", "logic"]
        name_lower = func_name.lower()
        if "sort" in name_lower:
            concepts.extend(["order", "compare"])
        if "search" in name_lower or "find" in name_lower:
            concepts.extend(["lookup", "match"])
        if "calculate" in name_lower or "compute" in name_lower:
            concepts.extend(["formula", "result"])
        return concepts

    # ── Phase 3 new helpers ─────────────────────────────────────

    def _create_function_question_from_profile(self, fp, code: str) -> Optional[VivaQuestion]:
        """Create a deep question using FunctionProfile (recursion / base case aware)."""
        from app.services.code_analyzer import FunctionProfile
        func_code = self._extract_function_code(code, fp.name)
        params = ', '.join(fp.param_names) if fp.param_names else '...'

        # Tailor the question based on detected structure
        if fp.calls_itself and not fp.has_base_case:
            q_text = (f"Your function `{fp.name}` calls itself but I don't see a clear base case. "
                      f"What stops the recursion — what input makes it stop?")
            concepts = ["recursion", "base_case", "termination", "infinite_recursion"]
            difficulty = 3
        elif fp.calls_itself:
            q_text = (f"Walk me through how `{fp.name}({params})` works on a small example, "
                      f"especially how and why the recursion stops.")
            concepts = ["recursion", "base_case", "call_stack", "return_value"]
            difficulty = 2
        elif fp.loop_count and fp.loop_count > 0:
            q_text = (f"Explain the loop inside `{fp.name}`. "
                      f"What does it iterate over and what does it accumulate or change?")
            concepts = ["iteration", "loop_body", "accumulation", "termination"]
            difficulty = 2
        elif not fp.has_return:
            q_text = (f"Your function `{fp.name}` doesn't seem to return a value. "
                      f"What is it supposed to produce and how does the caller get the result?")
            concepts = ["return_value", "side_effects", "functions"]
            difficulty = 2
        else:
            template = random.choice(self.TEMPLATES[QuestionType.FUNCTION_PURPOSE])
            q_text = template.format(name=fp.name)
            concepts = self._infer_function_concepts(fp.name, func_code)
            difficulty = 1

        return VivaQuestion(
            id="",
            question_type=QuestionType.FUNCTION_PURPOSE,
            question_text=q_text,
            target_code=func_code or f"def {fp.name}({params}): ...",
            target_line=fp.start_line if hasattr(fp, 'start_line') else None,
            expected_concepts=concepts,
            difficulty=difficulty,
        )

    def _create_algorithm_pattern_question(
        self, analysis: CodeAnalysisResult, code: str
    ) -> Optional[VivaQuestion]:
        """Ask about the algorithm choice based on detected pattern."""
        from app.services.code_analyzer import AlgorithmPattern
        pattern = analysis.algorithm_pattern
        snippet = code.split("\n")[0].strip()

        pattern_questions = {
            AlgorithmPattern.RECURSIVE: (
                "You chose a recursive approach here. "
                "What are the advantages and risks of recursion for this problem?",
                ["recursion", "stack_overflow", "base_case", "efficiency"]
            ),
            AlgorithmPattern.DYNAMIC_PROG: (
                "Your solution looks like dynamic programming. "
                "What sub-problem are you memoising and why does that help?",
                ["memoization", "subproblem", "overlapping", "optimal_substructure"]
            ),
            AlgorithmPattern.TWO_POINTER: (
                "You're using a two-pointer technique. "
                "What invariant do your left and right pointers maintain?",
                ["invariant", "convergence", "two_pointers", "linear_scan"]
            ),
            AlgorithmPattern.BRUTE_FORCE: (
                "Your solution uses nested loops — a brute-force approach. "
                "Can you estimate the time complexity and suggest a faster alternative?",
                ["time_complexity", "nested_loops", "optimization"]
            ),
        }

        default = (
            f"Why did you choose this approach for the problem? "
            f"Walk me through your reasoning.",
            ["reasoning", "algorithm_choice", "correctness"]
        )
        q_text, concepts = pattern_questions.get(pattern, default)
        # Add concepts_detected from AST as additional expected concepts
        if hasattr(analysis, 'concepts_detected'):
            concepts = list(set(concepts + analysis.concepts_detected))

        return VivaQuestion(
            id="",
            question_type=QuestionType.WHY_CHOICE,
            question_text=q_text,
            target_code=snippet,
            target_line=None,
            expected_concepts=concepts,
            difficulty=2,
        )

    def _create_issue_question(
        self, issue_loc, code_lines: List[str]
    ) -> Optional[VivaQuestion]:
        """Generate a question directly targeting a detected code issue."""
        line_num = issue_loc.line
        snippet = ""
        if line_num and 1 <= line_num <= len(code_lines):
            snippet = code_lines[line_num - 1].strip()

        q_text = (
            f"I noticed something on line {line_num}: `{snippet}`. "
            f"{issue_loc.description} "
            f"Can you explain what this part is supposed to do?"
        ) if line_num and snippet else (
            f"I noticed a potential issue in your code: {issue_loc.description}. "
            f"Can you walk me through your reasoning here?"
        )

        return VivaQuestion(
            id="",
            question_type=QuestionType.LINE_EXPLANATION,
            question_text=q_text,
            target_code=snippet or issue_loc.code_snippet or "",
            target_line=line_num,
            expected_concepts=[issue_loc.issue_type.value.replace('_', ' '),
                                "correctness", "logic"],
            difficulty=3,
        )


class SemanticVerifier:
    """
    Verifies if student's verbal explanation matches their code.
    
    Uses LLM to:
    1. Understand what the code actually does
    2. Parse the student's explanation
    3. Check semantic alignment (not exact word matching)
    4. Identify gaps in understanding
    """
    
    VERIFICATION_PROMPT = """You are evaluating a student's verbal explanation of their code.

FULL CODE SUBMITTED:
```python
{full_code}
```

CODE SEGMENT BEING DISCUSSED:
```python
{code}
```

AST ANALYSIS (ground truth about what the code actually does):
  Algorithm pattern : {algorithm_pattern}
  Concepts present  : {ast_concepts}
  Function summary  : {function_summary}
  Detected issues   : {detected_issues}

QUESTION ASKED:
{question}

STUDENT'S VERBAL RESPONSE (transcribed from audio):
"{response}"

EXPECTED CONCEPTS TO COVER:
{expected_concepts}

Evaluate if the student GENUINELY understands their code. The AST analysis above
is the ground truth — use it to judge whether the student's explanation is accurate.
Consider:
1. Does their explanation match what the AST says the code actually does?
2. Do they use appropriate terminology for the algorithm pattern?
3. Can they articulate WHY the code works (not just read it line-by-line)?
4. Are there any signs they did NOT write this code (vague, evasive, incorrect)?

Respond in this exact JSON format:
{{
    "score": 0.0,
    "matched_concepts": ["concepts they correctly explained"],
    "missing_concepts": ["concepts they missed or got wrong"],
    "understanding_level": "strong | adequate | weak | none",
    "feedback": "Brief constructive feedback for the student",
    "red_flags": ["any signs they didn't write this code"]
}}
"""
    
    def __init__(self):
        self.groq = GroqService()
    
    async def verify_answer(
        self,
        question: VivaQuestion,
        answer: StudentAnswer,
        full_code: str,
        analysis: Optional["CodeAnalysisResult"] = None,
    ) -> AnswerEvaluation:
        """
        Verify if student's answer demonstrates understanding.

        Phase 3 upgrade: if `analysis` (CodeAnalysisResult) is provided, the
        verification prompt is enriched with AST ground-truth so the LLM can
        judge accuracy against WHAT THE CODE ACTUALLY DOES.
        """
        # Build the enriched AST context strings (Phase 3)
        if analysis is not None:
            algorithm_pattern = getattr(analysis, 'algorithm_pattern', None)
            ap_str = algorithm_pattern.value if algorithm_pattern else "unknown"
            ast_concepts = ", ".join(getattr(analysis, 'concepts_detected', []) or ["N/A"])
            fn_profiles = getattr(analysis, 'function_profiles', [])
            fn_summary = "; ".join(
                f"{fp.name}({'recursive' if fp.calls_itself else 'iterative'}, "
                f"{'has base case' if fp.has_base_case else 'NO base case'})"
                for fp in fn_profiles
            ) if fn_profiles else "N/A"
            issue_locs = getattr(analysis, 'issue_locations', [])
            issues_str = "; ".join(
                f"{loc.issue_type.value} at line {loc.line}: {loc.description}"
                for loc in issue_locs
            ) if issue_locs else "none detected"
        else:
            ap_str = "unknown"
            ast_concepts = "N/A"
            fn_summary = "N/A"
            issues_str = "N/A"

        prompt = self.VERIFICATION_PROMPT.format(
            full_code=full_code,
            code=question.target_code or full_code,
            algorithm_pattern=ap_str,
            ast_concepts=ast_concepts,
            function_summary=fn_summary,
            detected_issues=issues_str,
            question=question.question_text,
            response=answer.transcribed_text,
            expected_concepts=", ".join(question.expected_concepts),
        )

        try:
            # Get LLM evaluation
            result = await self.groq.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert programming instructor evaluating student "
                            "understanding. Use the AST analysis as ground truth. Be fair but thorough."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            # Parse JSON response
            import json
            evaluation = json.loads(result)

            return AnswerEvaluation(
                question_id=question.id,
                score=float(evaluation.get("score", 0.5)),
                matched_concepts=evaluation.get("matched_concepts", []),
                missing_concepts=evaluation.get("missing_concepts", []),
                feedback=evaluation.get("feedback", ""),
                is_acceptable=float(evaluation.get("score", 0)) >= 0.5,
            )

        except Exception:
            # Fallback to basic keyword matching if LLM fails
            return self._fallback_verification(question, answer)

    async def verify_answer_with_ast(
        self,
        question: VivaQuestion,
        answer: StudentAnswer,
        full_code: str,
        analysis: "CodeAnalysisResult",
    ) -> AnswerEvaluation:
        """Convenience wrapper — always uses the rich AST path."""
        return await self.verify_answer(question, answer, full_code, analysis)

    def _fallback_verification(
        self,
        question: VivaQuestion,
        answer: StudentAnswer
    ) -> AnswerEvaluation:
        """Basic keyword-based verification fallback"""
        response_lower = answer.transcribed_text.lower()
        
        matched = []
        missing = []
        
        for concept in question.expected_concepts:
            if concept.lower() in response_lower:
                matched.append(concept)
            else:
                missing.append(concept)
        
        score = len(matched) / max(len(question.expected_concepts), 1)
        
        return AnswerEvaluation(
            question_id=question.id,
            score=score,
            matched_concepts=matched,
            missing_concepts=missing,
            feedback="Basic evaluation: Check if you covered all key concepts.",
            is_acceptable=score >= 0.5
        )

    # ── Deterministic concept-overlap scoring ─────────────────────

    def compute_concept_overlap(
        self,
        analysis: "CodeAnalysisResult",
        transcribed_text: str,
    ) -> dict:
        """
        Deterministic AST-vs-transcript concept comparison (FR-9).

        Step 1: Extract key concepts from AST analysis
        Step 2: Extract claimed concepts from student's transcript
        Step 3: Compute overlap score (Jaccard-like)

        Returns:
            {
                "ast_concepts": [...],
                "claimed_concepts": [...],
                "matched": [...],
                "missed": [...],
                "overlap_score": float (0-1),
                "confidence": "high" | "medium" | "low"
            }
        """
        import re

        # Step 1: Ground-truth concepts from AST
        ast_concepts = set()
        if hasattr(analysis, 'concepts_detected') and analysis.concepts_detected:
            ast_concepts.update(c.lower() for c in analysis.concepts_detected)
        if hasattr(analysis, 'algorithm_pattern') and analysis.algorithm_pattern:
            ast_concepts.add(analysis.algorithm_pattern.value.lower())
        for fp in getattr(analysis, 'function_profiles', []):
            if fp.calls_itself:
                ast_concepts.add("recursion")
            if fp.has_base_case:
                ast_concepts.add("base case")
            if fp.loop_count and fp.loop_count > 0:
                ast_concepts.add("iteration")
        for ds in getattr(analysis, 'data_structures_used', []):
            ast_concepts.add(ds.lower())
        for loc in getattr(analysis, 'issue_locations', []):
            ast_concepts.add(loc.issue_type.value.replace("_", " "))

        if not ast_concepts:
            ast_concepts = {"general programming"}

        # Step 2: Extract claimed concepts from transcript
        transcript_lower = transcribed_text.lower()
        # Concept synonyms to improve matching
        SYNONYMS = {
            "recursion": ["recursion", "recursive", "calls itself", "self-call"],
            "base case": ["base case", "base-case", "stopping condition", "termination", "base condition"],
            "iteration": ["loop", "iterate", "for loop", "while loop", "iteration", "iterating"],
            "loops": ["loop", "for", "while", "iterate", "looping"],
            "functions": ["function", "method", "def", "subroutine"],
            "conditionals": ["if", "else", "condition", "conditional", "branch"],
            "list": ["list", "array", "elements"],
            "dict": ["dictionary", "dict", "hash map", "key-value", "mapping"],
            "set": ["set", "unique", "distinct"],
            "tree": ["tree", "node", "binary tree", "bst"],
            "stack": ["stack", "lifo", "push", "pop"],
            "queue": ["queue", "fifo", "enqueue", "dequeue"],
            "sorting": ["sort", "sorting", "order", "sorted"],
            "searching": ["search", "find", "lookup", "binary search"],
            "dynamic_programming": ["dynamic programming", "dp", "memoization", "memo", "tabulation"],
            "divide_and_conquer": ["divide and conquer", "split", "merge", "halving"],
            "two_pointers": ["two pointer", "two-pointer", "left right", "converge"],
            "time_complexity": ["time complexity", "big o", "o(n)", "efficiency", "complexity"],
            "brute_force": ["brute force", "nested loop", "n squared", "naive"],
            "missing base case": ["base case", "missing base", "no base case"],
            "no termination": ["infinite loop", "doesn't stop", "no termination", "never ends"],
            "missing return": ["no return", "missing return", "doesn't return"],
        }

        claimed_concepts = set()
        for concept in ast_concepts:
            synonyms = SYNONYMS.get(concept, [concept])
            for synonym in synonyms:
                if synonym in transcript_lower:
                    claimed_concepts.add(concept)
                    break
            # Also try the concept itself if not in synonym map
            if concept not in claimed_concepts and concept in transcript_lower:
                claimed_concepts.add(concept)

        # Step 3: Compute overlap
        matched = ast_concepts & claimed_concepts
        missed = ast_concepts - claimed_concepts
        overlap_score = len(matched) / max(len(ast_concepts), 1)

        # Confidence based on transcript length and match quality
        word_count = len(transcript_lower.split())
        if word_count < 10:
            confidence = "low"
        elif overlap_score >= 0.6 and word_count >= 30:
            confidence = "high"
        elif overlap_score >= 0.3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "ast_concepts": sorted(ast_concepts),
            "claimed_concepts": sorted(claimed_concepts),
            "matched": sorted(matched),
            "missed": sorted(missed),
            "overlap_score": round(overlap_score, 3),
            "confidence": confidence,
        }


class VivaEngine:
    """
    Main Viva Voce examination engine.
    
    Workflow:
    1. Student submits code
    2. Engine analyzes code and generates questions
    3. Student records verbal answers
    4. Engine transcribes and verifies each answer
    5. Engine delivers final verdict
    """
    
    # Verdict thresholds
    PASS_THRESHOLD = 0.7        # Average score >= 70%
    WEAK_THRESHOLD = 0.4        # Average score 40-70%
    MIN_QUESTIONS = 2           # Minimum questions to answer
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.question_generator = QuestionGenerator()
        self.verifier = SemanticVerifier()
        self.sessions: Dict[str, VivaSession] = {}
    
    def start_session(
        self,
        session_id: str,
        student_id: str,
        code: str,
        num_questions: int = 3
    ) -> VivaSession:
        """
        Start a new Viva session for a student's code.
        
        Args:
            session_id: Unique session identifier
            student_id: Student identifier
            code: The code to examine
            num_questions: Number of questions to ask
            
        Returns:
            VivaSession object with generated questions
        """
        # Analyze the code
        analysis = self.analyzer.analyze_python(code)
        
        # Generate targeted questions
        questions = self.question_generator.generate_questions(
            code, analysis, num_questions
        )
        
        # Create session
        session = VivaSession(
            session_id=session_id,
            student_id=student_id,
            code=code,
            analysis=analysis,
            questions=questions
        )
        
        self.sessions[session_id] = session
        return session
    
    def get_current_question(self, session_id: str) -> Optional[VivaQuestion]:
        """Get the current question for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if session.current_question_index >= len(session.questions):
            return None
        
        return session.questions[session.current_question_index]
    
    async def submit_answer(
        self,
        session_id: str,
        transcribed_text: str,
        audio_duration: float
    ) -> AnswerEvaluation:
        """
        Submit and evaluate an answer for the current question.
        
        Args:
            session_id: Active session ID
            transcribed_text: Transcribed audio response
            audio_duration: Length of audio in seconds
            
        Returns:
            Evaluation of the answer
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        current_question = self.get_current_question(session_id)
        if not current_question:
            raise ValueError("No more questions in session")
        
        # Record the answer
        answer = StudentAnswer(
            question_id=current_question.id,
            transcribed_text=transcribed_text,
            audio_duration_seconds=audio_duration
        )
        session.answers.append(answer)
        
        # Evaluate the answer — pass full AST analysis for Phase 3 enriched verification
        evaluation = await self.verifier.verify_answer(
            current_question,
            answer,
            session.code,
            session.analysis,
        )
        session.evaluations.append(evaluation)
        
        # Move to next question
        session.current_question_index += 1
        
        return evaluation
    
    def get_verdict(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate final Viva verdict.
        
        Returns:
            Dict with verdict, scores, and detailed feedback
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if len(session.evaluations) < self.MIN_QUESTIONS:
            return {
                "verdict": VivaVerdict.INCONCLUSIVE.value,
                "message": f"Need at least {self.MIN_QUESTIONS} answers for verdict",
                "questions_answered": len(session.evaluations)
            }
        
        # Calculate average score
        total_score = sum(e.score for e in session.evaluations)
        avg_score = total_score / len(session.evaluations)
        
        # Determine verdict
        if avg_score >= self.PASS_THRESHOLD:
            verdict = VivaVerdict.PASS
            message = "Excellent! You demonstrated clear understanding of your code."
        elif avg_score >= self.WEAK_THRESHOLD:
            verdict = VivaVerdict.WEAK_UNDERSTANDING
            message = "You showed some understanding, but review the highlighted concepts."
        else:
            verdict = VivaVerdict.FAIL
            message = "You struggled to explain your code. Please review and resubmit."
        
        # Update session
        session.verdict = verdict
        session.completed_at = datetime.now()
        
        return {
            "verdict": verdict.value,
            "average_score": round(avg_score, 2),
            "message": message,
            "questions_answered": len(session.evaluations),
            "concept_overlap": self.verifier.compute_concept_overlap(
                session.analysis,
                " ".join(a.transcribed_text for a in session.answers),
            ),
            "question_breakdown": [
                {
                    "question": session.questions[i].question_text,
                    "score": session.evaluations[i].score,
                    "feedback": session.evaluations[i].feedback
                }
                for i in range(len(session.evaluations))
            ],
            "improvement_areas": self._get_improvement_areas(session)
        }
    
    def _get_improvement_areas(self, session: VivaSession) -> List[str]:
        """Identify areas for improvement based on evaluations"""
        areas = []
        
        # Collect all missing concepts
        all_missing = []
        for evaluation in session.evaluations:
            all_missing.extend(evaluation.missing_concepts)
        
        # Count frequencies
        from collections import Counter
        missing_counts = Counter(all_missing)
        
        # Top 3 areas to improve
        for concept, count in missing_counts.most_common(3):
            areas.append(f"Review: {concept}")
        
        return areas


# Singleton instance
viva_engine = VivaEngine()
