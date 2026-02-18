"""
Deep Integration Bridge — Central Orchestrator for SapioCode

Connects all three roles into a single pipeline:
  Role 1 (Systems Architect) : Code execution backend   → POST :8000/run
  Role 2 (AI Engineer / YOU) : AST analysis, Socratic tutoring, Viva
  Role 3 (Data Architect)    : BKT mastery in Neo4j     → POST :8001/submit

Pipeline per student submission:
  ┌────────────────────────────────────────────────────────────────┐
  │ 1. Receive code + affect data from frontend                   │
  │ 2. Execute code via Role 1 (or local fallback)                │
  │ 3. AST-analyze code (Role 2)                                  │
  │ 4. Compute cognitive state from affect (mirrors Role 3)       │
  │ 5. Run local BKT update (mirrors Role 3's math)               │
  │ 6. Forward to Role 3's Neo4j for persistence (best-effort)    │
  │ 7. Decide Socratic intervention based on mastery + affect     │
  │ 8. Generate frustration-aware hint if needed                  │
  │ 9. Return unified response to frontend                        │
  └────────────────────────────────────────────────────────────────┘
"""
import httpx
import subprocess
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from app.services.code_analyzer import CodeAnalyzer, CodeAnalysisResult
from app.services.tutoring_engine import (
    TutoringEngine, HintGenerator, StudentContext, HintLevel
)
from app.services.groq_service import get_groq_service
from app.services.bkt_local import get_local_bkt, LocalBKTEngine
from app.services.affect_adapter import get_affect_adapter, AffectAdapter
from app.services.session_store import get_session_store, HintRecord
from app.core.config import get_settings

_settings = get_settings()

# ═══════════════════════════════════════════════════
# Service URLs  (loaded from .env via config.py)
# ═══════════════════════════════════════════════════
EXECUTION_BACKEND_URL = _settings.EXECUTION_BACKEND_URL   # Role 1
BKT_BACKEND_URL       = _settings.BKT_BACKEND_URL         # Role 3


# ═══════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════

@dataclass
class CodeSubmission:
    """Full context for a student's code submission"""
    student_id: str
    submission_id: str
    problem_description: str
    code: str
    language: str = "python"
    stdin: str = ""
    concepts: List[str] = field(default_factory=list)  # e.g. ["loops", "arrays"]

    # Student struggle context
    time_stuck: int = 0
    previous_hints: int = 0
    code_attempts: int = 0


@dataclass
class CognitiveState:
    """
    Cognitive state from Role 3's Affective Perception.
    Can be computed from raw Face-API expressions or sent directly.
    """
    frustration: float = 0.1
    engagement: float = 0.7
    confusion: float = 0.2
    boredom: float = 0.0

    def to_dict(self) -> dict:
        return {
            "frustration": self.frustration,
            "engagement": self.engagement,
            "confusion": self.confusion,
            "boredom": self.boredom
        }


@dataclass
class ExecutionResult:
    """Result from code execution (Role 1 or local)"""
    status: str        # "OK" | "RTE" | "TLE" | "UNAVAILABLE"
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None


@dataclass
class IntegratedFeedback:
    """Complete response returned to the frontend"""
    # ── Execution (Role 1) ──
    execution_status: str
    stdout: str
    stderr: str

    # ── AST Analysis (Role 2) ──
    code_is_valid: bool
    complexity_score: int
    detected_issues: List[str]
    code_structure: dict

    # ── Socratic Guidance (Role 2) ──
    should_intervene: bool
    hint: Optional[str]
    hint_level: int
    intervention_reason: str

    # ── BKT Mastery (Role 3 math, local compute) ──
    mastery_updates: dict
    bkt_synced_to_neo4j: bool

    # ── Affect (Role 3 perception) ──
    cognitive_state: dict
    affect_intervention: dict

    def to_dict(self) -> dict:
        return {
            "execution": {
                "status": self.execution_status,
                "stdout": self.stdout,
                "stderr": self.stderr,
            },
            "analysis": {
                "code_is_valid": self.code_is_valid,
                "complexity_score": self.complexity_score,
                "detected_issues": self.detected_issues,
                "code_structure": self.code_structure,
            },
            "tutoring": {
                "should_intervene": self.should_intervene,
                "hint": self.hint,
                "hint_level": self.hint_level,
                "reason": self.intervention_reason,
            },
            "mastery": {
                "updates": self.mastery_updates,
                "synced_to_neo4j": self.bkt_synced_to_neo4j,
            },
            "affect": {
                "cognitive_state": self.cognitive_state,
                "intervention": self.affect_intervention,
            },
        }


# ═══════════════════════════════════════════════════
# Integration Bridge  (the orchestrator)
# ═══════════════════════════════════════════════════

class IntegrationBridge:
    """
    Central orchestrator connecting all three roles.

    Design decisions:
    - BKT runs LOCALLY first (instant), then syncs to Role 3 async
    - Code execution calls Role 1 first, falls back to local subprocess
    - Affect data is smoothed server-side using Role 3's exact algorithm
    - Hints are modulated by both mastery AND frustration
    """

    def __init__(self):
        self.analyzer       = CodeAnalyzer()
        self.tutor_engine   = TutoringEngine()
        self.hint_generator = HintGenerator(get_groq_service())
        self.bkt_engine     = get_local_bkt()
        self.affect_adapter = get_affect_adapter()
        self.session_store  = get_session_store()

        # Session hint history per student (in-memory + SQLite persistence)
        self._hint_history: Dict[str, List[dict]] = {}

    # ══════════════════════════════════════════════
    # MAIN PIPELINE
    # ══════════════════════════════════════════════

    async def process_submission(
        self,
        submission: CodeSubmission,
        cognitive_state: CognitiveState
    ) -> IntegratedFeedback:
        """
        Full SapioCode pipeline for one student code submission.

        Steps:
        1. Execute code (Role 1 → fallback local)
        2. AST analysis (Role 2)
        3. Process affect data (Role 3 math)
        4. Run local BKT update (Role 3 math)
        5. Sync to Role 3's Neo4j (best-effort)
        6. Decide Socratic intervention (Role 2)
        7. Generate frustration-aware hint (Role 2)
        8. Return unified response
        """

        # ── Step 1: Execute code via Role 1 ──
        exec_result = await self._execute_code(submission.code, submission.stdin)

        # ── Step 2: AST analysis ──
        analysis = self.analyzer.analyze_python(submission.code)

        # ── Step 3: Process affect ──
        smoothed_affect = self.affect_adapter.process_cognitive_state(
            submission.student_id,
            cognitive_state.to_dict()
        )
        affect_decision = self.affect_adapter.should_intervene(submission.student_id)

        # ── Step 4: Local BKT update ──
        code_correct = exec_result.status == "OK"
        concepts = submission.concepts or self._infer_concepts(analysis)

        mastery_results = {}
        if concepts:
            mastery_results = self.bkt_engine.process_submission(
                student_id=submission.student_id,
                concepts=concepts,
                correct=code_correct,
                cognitive_state=smoothed_affect
            )

        # ── Step 5: Sync to Role 3's Neo4j (best-effort) ──
        neo4j_synced = await self._sync_to_role3_bkt(
            student_id=submission.student_id,
            submission_id=submission.submission_id,
            correct=code_correct,
            cognitive_state=smoothed_affect
        )

        # ── Step 6: Decide Socratic intervention ──
        # Use MASTERY to influence hint level
        avg_mastery = 0.5
        if mastery_results:
            avg_mastery = sum(
                r["new_mastery"] for r in mastery_results.values()
            ) / len(mastery_results)

        # Adjust frustration based on affect
        effective_frustration = smoothed_affect.get("frustration", 0.1)

        student_ctx = StudentContext(
            problem_description=submission.problem_description,
            current_code=submission.code,
            time_stuck=submission.time_stuck,
            frustration_level=effective_frustration,
            previous_hints=submission.previous_hints,
            code_attempts=submission.code_attempts
        )

        decision = self.tutor_engine.decide_intervention(student_ctx)

        # ── Step 7: Generate hint if needed ──
        hint = None
        actual_hint_level = decision.hint_level

        if decision.should_intervene or affect_decision["intervene"]:
            # Adjust hint level based on mastery
            if avg_mastery < 0.3:
                # Low mastery → escalate to more direct hints
                actual_hint_level = HintLevel(min(
                    decision.hint_level.value + 1, HintLevel.DIRECT_HINT.value
                ))
            elif avg_mastery > 0.7:
                # High mastery → keep Socratic
                actual_hint_level = HintLevel.SOCRATIC_QUESTION

            # Adjust based on affect
            level_adj = affect_decision.get("hint_level_adjustment", 0)
            adjusted_value = min(max(
                actual_hint_level.value + level_adj, 1
            ), 4)
            actual_hint_level = HintLevel(adjusted_value)

            hint = await self.hint_generator.generate_hint_for_student(
                student_id=submission.student_id,
                level=actual_hint_level,
                problem=submission.problem_description,
                code=submission.code,
                analysis=analysis,  # Pass full CodeAnalysisResult for deep AST path
            )

            # Apply affect-based tone adjustment
            hint = self.affect_adapter.adjust_hint_tone(
                hint, submission.student_id
            )

            # Track hint history
            self._record_hint(
                submission.student_id,
                hint,
                actual_hint_level,
                decision.reason
            )

        # ── Step 8: Build unified response ──
        return IntegratedFeedback(
            # Execution
            execution_status=exec_result.status,
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,

            # AST Analysis
            code_is_valid=analysis.is_valid,
            complexity_score=analysis.complexity_score,
            detected_issues=[i.value for i in analysis.issues],
            code_structure=analysis.code_structure,

            # Socratic Guidance
            should_intervene=decision.should_intervene or affect_decision["intervene"],
            hint=hint,
            hint_level=actual_hint_level.value,
            intervention_reason=(
                decision.reason
                + (f" + {affect_decision['reason']}" if affect_decision["intervene"] else "")
            ),

            # BKT Mastery
            mastery_updates=mastery_results,
            bkt_synced_to_neo4j=neo4j_synced,

            # Affect
            cognitive_state=smoothed_affect,
            affect_intervention=affect_decision,
        )

    # ══════════════════════════════════════════════
    # ROLE 1: Code Execution
    # ══════════════════════════════════════════════

    async def _execute_code(self, code: str, stdin: str = "") -> ExecutionResult:
        """
        Execute code via Role 1's backend.
        Falls back to local subprocess if Role 1 is offline.
        """
        # Try Role 1 first
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{EXECUTION_BACKEND_URL}/run",
                    json={"code": code, "stdin": stdin}
                )
                response.raise_for_status()
                data = response.json()
                return ExecutionResult(
                    status=data.get("status", "RTE"),
                    stdout=data.get("stdout", ""),
                    stderr=data.get("stderr", ""),
                    exit_code=data.get("exit_code")
                )
        except httpx.ConnectError:
            pass  # Role 1 offline, try local fallback
        except Exception as e:
            print(f"[Bridge] Role 1 execution error: {e}")

        # Local fallback (subprocess with 5s timeout, mirrors Role 1's logic)
        return self._execute_locally(code, stdin)

    def _execute_locally(self, code: str, stdin: str = "") -> ExecutionResult:
        """
        Local code execution fallback.
        Mirrors Role 1's backend/main.py: subprocess, 5s timeout, OK/RTE/TLE.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=5  # Same 5s timeout as Role 1
            )
            return ExecutionResult(
                status="OK" if result.returncode == 0 else "RTE",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="TLE",
                stdout="",
                stderr="Execution timed out (5 second limit)",
                exit_code=None
            )
        except Exception as e:
            return ExecutionResult(
                status="RTE",
                stdout="",
                stderr=str(e),
                exit_code=1
            )

    # ══════════════════════════════════════════════
    # ROLE 3: BKT Sync to Neo4j
    # ══════════════════════════════════════════════

    async def _sync_to_role3_bkt(
        self,
        student_id: str,
        submission_id: str,
        correct: bool,
        cognitive_state: dict
    ) -> bool:
        """
        Forward submission to Role 3's BKT endpoint for Neo4j persistence.
        This is best-effort — we already have the local BKT result.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{BKT_BACKEND_URL}/submit",
                    json={
                        "sid": student_id,
                        "sub_id": submission_id,
                        "correct": correct,
                        "cognitive_state": cognitive_state
                    }
                )
                response.raise_for_status()
                return True
        except httpx.ConnectError:
            print("[Bridge] Role 3 BKT offline — local BKT used instead")
            return False
        except Exception as e:
            print(f"[Bridge] Role 3 BKT sync failed: {e}")
            return False

    # ══════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════

    def _infer_concepts(self, analysis: CodeAnalysisResult) -> List[str]:
        """
        Infer concepts from AST analysis when not explicitly provided.
        This connects the AST (Role 2) to the knowledge graph (Role 3).
        """
        concepts = []
        if analysis.has_recursion:
            concepts.append("recursion")
        if analysis.loop_count > 0:
            concepts.append("loops")
        if analysis.function_count > 0:
            concepts.append("functions")
        if analysis.code_structure.get("conditionals", 0) > 0:
            concepts.append("conditionals")
        if analysis.variable_count > 3:
            concepts.append("variables")

        # Check for specific patterns via structure
        structure = analysis.code_structure
        funcs = structure.get("functions", [])
        for fname in funcs:
            fname_lower = fname.lower()
            if "sort" in fname_lower:
                concepts.append("sorting")
            if "search" in fname_lower or "find" in fname_lower:
                concepts.append("searching")
            if "tree" in fname_lower or "node" in fname_lower:
                concepts.append("trees")
            if "list" in fname_lower or "linked" in fname_lower:
                concepts.append("linked_lists")

        return concepts if concepts else ["general_programming"]

    def _record_hint(
        self,
        student_id: str,
        hint: str,
        level: HintLevel,
        reason: str
    ):
        """Record hint in session history (in-memory + SQLite persistence)"""
        if student_id not in self._hint_history:
            self._hint_history[student_id] = []

        entry = {
            "hint": hint,
            "level": level.value,
            "level_name": level.name,
            "reason": reason,
        }
        self._hint_history[student_id].append(entry)

        # Persist to SQLite for cross-restart durability
        try:
            self.session_store.record_hint(HintRecord(
                student_id=student_id,
                session_id=f"{student_id}_session",
                hint_text=hint,
                hint_level=level.value,
                hint_path=reason,
                teaching_focus=level.name,
            ))
        except Exception:
            pass  # Best-effort — don't break pipeline if SQLite fails

    def get_hint_history(self, student_id: str) -> List[dict]:
        """Get all hints given to a student (in-memory + SQLite fallback)."""
        # Return in-memory if available (current session), else fall back to SQLite
        in_memory = self._hint_history.get(student_id, [])
        if in_memory:
            return in_memory
        try:
            return self.session_store.get_hint_history(student_id)
        except Exception:
            return []

    # ══════════════════════════════════════════════
    # STANDALONE HINT (no submission)
    # ══════════════════════════════════════════════

    async def generate_standalone_hint(
        self,
        student_id: str,
        problem_description: str,
        code: str,
        time_stuck: int = 60,
        previous_hints: int = 0
    ) -> dict:
        """
        Generate a Socratic hint without running the full submission pipeline.
        Used when the student clicks "Get Hint" during coding.
        """
        # AST analysis
        analysis = self.analyzer.analyze_python(code)

        # Get smoothed affect
        smoothed = self.affect_adapter.get_smoothed_state(student_id)
        affect_decision = self.affect_adapter.should_intervene(student_id)

        # Get current mastery
        all_mastery = self.bkt_engine.get_all_mastery(student_id)
        avg_mastery = sum(all_mastery.values()) / max(len(all_mastery), 1) if all_mastery else 0.5

        # Build student context
        context = StudentContext(
            problem_description=problem_description,
            current_code=code,
            time_stuck=time_stuck,
            frustration_level=smoothed.get("frustration", 0.1),
            previous_hints=previous_hints,
            code_attempts=0
        )

        decision = self.tutor_engine.decide_intervention(context)
        hint_level = decision.hint_level

        # Adjust for mastery
        if avg_mastery < 0.3:
            hint_level = HintLevel(min(hint_level.value + 1, 4))

        # Generate hint (deep AST path with conversation memory)
        hint = await self.hint_generator.generate_hint_for_student(
            student_id=student_id,
            level=hint_level,
            problem=problem_description,
            code=code,
            analysis=analysis,  # Pass full CodeAnalysisResult for code-specific hints
        )

        # Tone adjustment
        hint = self.affect_adapter.adjust_hint_tone(hint, student_id)

        self._record_hint(student_id, hint, hint_level, decision.reason)

        return {
            "hint": hint,
            "hint_level": hint_level.value,
            "hint_level_name": hint_level.name,
            "should_intervene": decision.should_intervene,
            "reason": decision.reason,
            "mastery_snapshot": all_mastery,
            "cognitive_state": smoothed,
        }


# ── Singleton ──────────────────────────────────
_bridge_instance: Optional[IntegrationBridge] = None


def get_integration_bridge() -> IntegrationBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = IntegrationBridge()
    return _bridge_instance
