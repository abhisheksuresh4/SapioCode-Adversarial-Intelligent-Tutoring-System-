"""Socratic Tutoring Engine - Decides when and how to intervene"""
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


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
    """Generates hints at different levels using Groq"""
    
    def __init__(self, groq_service):
        self.groq = groq_service
    
    async def generate_hint(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Generate a hint at the specified level
        
        Args:
            level: Hint level (Socratic to Direct)
            problem: Problem description
            code: Student's current code
            analysis: Code analysis results
            
        Returns:
            Generated hint string
        """
        prompt = self._build_prompt(level, problem, code, analysis)
        
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt(level)
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await self.groq.chat_completion(messages, temperature=0.7)
        return response
    
    def _get_system_prompt(self, level: HintLevel) -> str:
        """Get system prompt based on hint level"""
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
            )
        }
        return prompts.get(level, prompts[HintLevel.SOCRATIC_QUESTION])
    
    def _build_prompt(
        self,
        level: HintLevel,
        problem: str,
        code: str,
        analysis: Dict[str, Any]
    ) -> str:
        """Build the hint generation prompt"""
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
