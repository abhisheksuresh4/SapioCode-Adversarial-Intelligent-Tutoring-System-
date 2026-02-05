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
        Generate Viva questions based on code analysis.
        
        Args:
            code: The student's submitted code
            analysis: AST analysis result
            num_questions: How many questions to generate
            
        Returns:
            List of VivaQuestion objects
        """
        questions = []
        code_lines = code.split("\n")
        
        # Priority 1: Ask about functions (most important)
        functions = analysis.code_structure.get("functions", [])
        for func_name in functions[:2]:
            q = self._create_function_question(func_name, code)
            if q:
                questions.append(q)
        
        # Priority 2: Ask about loops (common confusion point)
        if analysis.loop_count > 0:
            q = self._create_loop_question(code_lines, analysis)
            if q:
                questions.append(q)
        
        # Priority 3: Ask about key variables
        variables = self._extract_variables(code)
        for var in variables[:1]:
            q = self._create_variable_question(var, code)
            if q:
                questions.append(q)
        
        # Priority 4: Edge case question (tests deep understanding)
        q = self._create_edge_case_question(code, analysis)
        if q:
            questions.append(q)
        
        # Shuffle and limit
        random.shuffle(questions)
        questions = questions[:num_questions]
        
        # Assign IDs
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
        
        # Add specific concepts based on function name
        name_lower = func_name.lower()
        if "sort" in name_lower:
            concepts.extend(["order", "compare"])
        if "search" in name_lower or "find" in name_lower:
            concepts.extend(["lookup", "match"])
        if "calculate" in name_lower or "compute" in name_lower:
            concepts.extend(["formula", "result"])
        
        return concepts


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

CODE BEING DISCUSSED:
```python
{code}
```

QUESTION ASKED:
{question}

STUDENT'S VERBAL RESPONSE (transcribed from audio):
"{response}"

EXPECTED CONCEPTS TO COVER:
{expected_concepts}

Evaluate if the student understands their code. Consider:
1. Do they explain the core logic correctly?
2. Do they use appropriate terminology?
3. Can they articulate what the code does (not just read it)?
4. Do they understand WHY the code works?

Respond in this exact JSON format:
{{
    "score": 0.0 to 1.0,
    "matched_concepts": ["list", "of", "concepts", "they", "demonstrated"],
    "missing_concepts": ["concepts", "they", "missed"],
    "understanding_level": "strong" | "adequate" | "weak" | "none",
    "feedback": "Brief constructive feedback for the student",
    "red_flags": ["any", "signs", "they", "didnt", "write", "this"]
}}
"""
    
    def __init__(self):
        self.groq = GroqService()
    
    async def verify_answer(
        self,
        question: VivaQuestion,
        answer: StudentAnswer,
        full_code: str
    ) -> AnswerEvaluation:
        """
        Verify if student's answer demonstrates understanding.
        
        Args:
            question: The question that was asked
            answer: Student's transcribed response
            full_code: Complete code for context
            
        Returns:
            AnswerEvaluation with score and feedback
        """
        prompt = self.VERIFICATION_PROMPT.format(
            code=question.target_code or full_code,
            question=question.question_text,
            response=answer.transcribed_text,
            expected_concepts=", ".join(question.expected_concepts)
        )
        
        try:
            # Get LLM evaluation
            result = await self.groq.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert programming instructor evaluating student understanding. Be fair but thorough."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
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
                is_acceptable=float(evaluation.get("score", 0)) >= 0.5
            )
            
        except Exception as e:
            # Fallback to basic keyword matching if LLM fails
            return self._fallback_verification(question, answer)
    
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
        
        # Evaluate the answer
        evaluation = await self.verifier.verify_answer(
            current_question,
            answer,
            session.code
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
