"""Socratic Tutoring Engine - Decides when and how to intervene"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone

if TYPE_CHECKING:
    from app.services.code_analyzer import CodeAnalysisResult
    from app.services.ast_tutor import TutoringContext


class TutoringState(Enum):
    """States in the tutoring state machine"""
    OBSERVING = "observing"  # Watching student code
    ANALYZING = "analyzing"  # Analyzing code for issues
    DECIDING = "deciding"    # Deciding if intervention needed
    HINTING = "hinting"      # Generating hint
    WAITING = "waiting"      # Waiting for student response


class HintLevel(Enum):
    """Levels of hints - Socratic method hierarchy"""
    SOCRATIC_QUESTION = 1    # Ask guiding question (don't reveal)
    CONCEPTUAL_NUDGE = 2     # Point to relevant concept
    PSEUDO_CODE = 3          # Provide algorithmic direction
    DIRECT_HINT = 4          # More explicit guidance


@dataclass
class StudentContext:
    """Context about the student's current state"""
    problem_description: str
    current_code: str
    time_stuck: int  # seconds
    frustration_level: float  # 0.0 to 1.0
    previous_hints: int
    code_attempts: int
    last_change_time: Optional[datetime] = None


@dataclass
class InterventionDecision:
    """Decision whether to intervene and how"""
    should_intervene: bool
    reason: str
    hint_level: HintLevel
    urgency: float  # 0.0 to 1.0


class TutoringEngine:
    """
    Main tutoring engine that decides WHEN to intervene
    Uses a state machine to manage the tutoring flow
    """
    
    def __init__(self):
        self.state = TutoringState.OBSERVING
        self.min_stuck_time = 30  # seconds
        self.max_stuck_time = 180  # 3 minutes
        self.frustration_threshold = 0.6
    
    def decide_intervention(self, context: StudentContext) -> InterventionDecision:
        """
        Decide if intervention is needed based on student context
        
        Args:
            context: Current student state
            
        Returns:
            InterventionDecision with action plan
        """
        # Don't intervene too quickly
        if context.time_stuck < self.min_stuck_time:
            return InterventionDecision(
                should_intervene=False,
                reason="Student hasn't been stuck long enough",
                hint_level=HintLevel.SOCRATIC_QUESTION,
                urgency=0.0
            )
        
        # Calculate urgency based on multiple factors
        urgency = self._calculate_urgency(context)
        
        # Decide hint level based on previous hints and frustration
        hint_level = self._determine_hint_level(context)
        
        # Intervention triggers
        triggers = []
        
        # Trigger 1: Stuck too long
        if context.time_stuck > self.max_stuck_time:
            triggers.append("stuck_too_long")
        
        # Trigger 2: High frustration
        if context.frustration_level > self.frustration_threshold:
            triggers.append("high_frustration")
        
        # Trigger 3: No progress after multiple attempts
        if context.code_attempts > 5 and context.time_stuck > 60:
            triggers.append("multiple_failed_attempts")
        
        # Trigger 4: Medium stuck time with some frustration
        if context.time_stuck > 60 and context.frustration_level > 0.4:
            triggers.append("moderate_struggle")
        
        should_intervene = len(triggers) > 0
        
        return InterventionDecision(
            should_intervene=should_intervene,
            reason=", ".join(triggers) if triggers else "no_triggers",
            hint_level=hint_level,
            urgency=urgency
        )
    
    def _calculate_urgency(self, context: StudentContext) -> float:
        """Calculate intervention urgency (0.0 to 1.0)"""
        # Time factor (0-1)
        time_factor = min(context.time_stuck / self.max_stuck_time, 1.0)
        
        # Frustration factor (0-1)
        frustration_factor = context.frustration_level
        
        # Attempt factor (more attempts = more urgent)
        attempt_factor = min(context.code_attempts / 10, 1.0)
        
        # Weighted average
        urgency = (
            time_factor * 0.4 +
            frustration_factor * 0.4 +
            attempt_factor * 0.2
        )
        
        return min(urgency, 1.0)
    
    def _determine_hint_level(self, context: StudentContext) -> HintLevel:
        """
        Determine appropriate hint level based on context
        Escalate hints if student still stuck
        """
        # Start with Socratic questions
        if context.previous_hints == 0:
            return HintLevel.SOCRATIC_QUESTION
        
        # Escalate based on frustration and time
        if context.frustration_level > 0.8 or context.time_stuck > 240:
            return HintLevel.DIRECT_HINT
        
        if context.frustration_level > 0.6 or context.previous_hints >= 2:
            return HintLevel.PSEUDO_CODE
        
        if context.previous_hints >= 1:
            return HintLevel.CONCEPTUAL_NUDGE
        
        return HintLevel.SOCRATIC_QUESTION
    
    def transition_state(self, event: str, context: Dict[str, Any]) -> TutoringState:
        """
        Handle state transitions in the tutoring flow
        
        Args:
            event: Event that triggers transition
            context: Additional context for decision
            
        Returns:
            New state
        """
        transitions = {
            TutoringState.OBSERVING: {
                "code_changed": TutoringState.OBSERVING,
                "stuck_detected": TutoringState.ANALYZING,
                "student_idle": TutoringState.ANALYZING
            },
            TutoringState.ANALYZING: {
                "analysis_complete": TutoringState.DECIDING,
                "syntax_error": TutoringState.DECIDING
            },
            TutoringState.DECIDING: {
                "intervention_needed": TutoringState.HINTING,
                "no_intervention": TutoringState.OBSERVING
            },
            TutoringState.HINTING: {
                "hint_sent": TutoringState.WAITING
            },
            TutoringState.WAITING: {
                "code_changed": TutoringState.OBSERVING,
                "still_stuck": TutoringState.ANALYZING,
                "timeout": TutoringState.ANALYZING
            }
        }
        
        if event in transitions.get(self.state, {}):
            new_state = transitions[self.state][event]
            self.state = new_state
            return new_state
        
        return self.state


class HintGenerator:
    """
    Generates Socratic hints using deep AST context + conversation memory.

    Phase 2 upgrade:
    - Accepts a full CodeAnalysisResult (not just a shallow dict)
    - Uses ASTTutor to identify the best teaching moment
    - Injects conversation history for multi-turn dialogue
    - Produces code-SPECIFIC questions referencing real variable names + line numbers
    """

    def __init__(self, groq_service):
        self.groq = groq_service
        # Lazy import to avoid circular dependency
        from app.services.ast_tutor import ASTTutor, ConversationMemory
        self._ast_tutor = ASTTutor()
        self._memory = ConversationMemory(max_turns=20)

    # ── Main entry point ──────────────────────────────────────────

    async def generate_hint(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis,  # CodeAnalysisResult | dict — both supported
    ) -> str:
        """
        Generate a hint at the specified level.
        Works with BOTH:
          - new CodeAnalysisResult (Phase 2 deep analysis)
          - old dict (legacy callers — falls back gracefully)
        """
        # If we received a proper CodeAnalysisResult, use deep path
        from app.services.code_analyzer import CodeAnalysisResult as CAR
        if isinstance(analysis, CAR):
            return await self._generate_deep_hint(level, problem, code, analysis)

        # Legacy fallback (dict-based)
        return await self._generate_legacy_hint(level, problem, code, analysis)

    async def generate_hint_for_student(
        self,
        student_id: str,
        level: HintLevel,
        problem: str,
        code: str,
        analysis,
    ) -> str:
        """
        Generate a hint WITH conversation memory tracking.
        Use this instead of generate_hint when you have a student_id.
        """
        from app.services.code_analyzer import CodeAnalysisResult as CAR
        history = self._memory.get_history(student_id, last_n=6)

        if isinstance(analysis, CAR):
            # Build full tutoring context with conversation history
            ctx = self._ast_tutor.build_context(
                analysis, code, problem, history
            )
            hint = await self._invoke_llm_with_context(ctx, level.value)
        else:
            hint = await self._generate_legacy_hint(level, problem, code, analysis)

        # Record this turn
        from app.services.ast_tutor import ConversationTurn
        self._memory.add_turn(student_id, ConversationTurn(
            role="tutor",
            content=hint,
            hint_level=level.value,
            teaching_focus=self._get_focus(analysis),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        return hint

    def record_student_message(self, student_id: str, message: str) -> None:
        """Record a student's message (code submission, question) into memory."""
        from app.services.ast_tutor import ConversationTurn
        self._memory.add_turn(student_id, ConversationTurn(
            role="student",
            content=message,
            hint_level=0,
            teaching_focus="",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    def get_conversation_summary(self, student_id: str) -> Dict[str, Any]:
        return self._memory.summary(student_id)

    def get_hint_count(self, student_id: str) -> int:
        return self._memory.get_hint_count(student_id)

    # ── Deep path (Phase 2) ───────────────────────────────────────

    async def _generate_deep_hint(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis,  # CodeAnalysisResult
    ) -> str:
        ctx = self._ast_tutor.build_context(analysis, code, problem)
        return await self._invoke_llm_with_context(ctx, level.value)

    async def _invoke_llm_with_context(
        self,
        ctx: "TutoringContext",
        hint_level: int,
    ) -> str:
        """Invoke the LLM with the full tutoring context."""
        user_prompt = ctx.to_llm_prompt(hint_level)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._get_system_prompt_deep(hint_level)}
        ]

        # Inject last few conversation turns BEFORE the current prompt
        if ctx.conversation_history:
            messages.extend(ctx.conversation_history)

        messages.append({"role": "user", "content": user_prompt})

        response = await self.groq.chat_completion(messages, temperature=0.7)
        return response

    def _get_system_prompt_deep(self, level: int) -> str:
        base = (
            "You are SapioCode, an intelligent Socratic coding tutor. "
            "You have been given a deep AST analysis of the student's code. "
            "Always reference SPECIFIC elements from their code (function names, "
            "variable names, line numbers) — never give generic advice. "
        )
        level_addons = {
            1: "Ask ONE concise guiding question. Never give the answer or show code.",
            2: "Point to the relevant concept with a brief example unrelated to their problem.",
            3: "Give structural pseudo-code guidance. Use their actual variable/function names.",
            4: "Be explicit. You may show a partial code snippet with blanks (`____`) for them to fill.",
        }
        return base + level_addons.get(level, level_addons[1])

    # ── Legacy fallback ───────────────────────────────────────────

    async def _generate_legacy_hint(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis: Dict[str, Any],
    ) -> str:
        prompt = self._build_legacy_prompt(level, problem, code, analysis)
        messages = [
            {"role": "system", "content": self._get_system_prompt(level)},
            {"role": "user", "content": prompt},
        ]
        return await self.groq.chat_completion(messages, temperature=0.7)

    def _get_focus(self, analysis) -> str:
        from app.services.code_analyzer import CodeAnalysisResult as CAR
        if isinstance(analysis, CAR) and analysis.issue_locations:
            return analysis.issue_locations[0].issue_type.value
        return "general"

    # ── Old system prompt kept for backward compat ────────────────

    def _get_system_prompt(self, level: HintLevel) -> str:
        prompts = {
            HintLevel.SOCRATIC_QUESTION: (
                "You are a Socratic tutor. Ask guiding questions that make the student "
                "think critically. NEVER give direct answers or show code. "
                "Your goal is to help them discover the solution themselves."
            ),
            HintLevel.CONCEPTUAL_NUDGE: (
                "You are a patient programming tutor. Point the student toward the "
                "relevant concept or algorithm they need. Give examples of the concept "
                "but not the exact solution to their problem."
            ),
            HintLevel.PSEUDO_CODE: (
                "You are a programming mentor. Provide algorithmic guidance in pseudo-code "
                "or high-level steps. Don't write the actual code, but show the structure."
            ),
            HintLevel.DIRECT_HINT: (
                "You are a supportive coding instructor. The student is very stuck. "
                "Provide more explicit guidance, possibly with code snippets, but still "
                "leave some gaps for them to fill."
            ),
        }
        return prompts.get(level, prompts[HintLevel.SOCRATIC_QUESTION])

    def _build_legacy_prompt(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis: Dict[str, Any],
    ) -> str:
        prompt = f"""PROBLEM:
{problem}

STUDENT'S CODE:
```python
{code}
```

CODE ANALYSIS:
- Functions: {analysis.get('function_count', 0)}
- Loops: {analysis.get('loop_count', 0)}
- Issues detected: {', '.join(str(i) for i in analysis.get('issues', []))}

The student appears to be stuck. """
        if level == HintLevel.SOCRATIC_QUESTION:
            prompt += "Ask ONE guiding question that will help them think about the next step."
        elif level == HintLevel.CONCEPTUAL_NUDGE:
            prompt += "Point them toward the concept or technique they need to use."
        elif level == HintLevel.PSEUDO_CODE:
            prompt += "Provide pseudo-code or algorithmic steps they should follow."
        else:
            prompt += "Give them explicit guidance to help them make progress."
        return prompt

