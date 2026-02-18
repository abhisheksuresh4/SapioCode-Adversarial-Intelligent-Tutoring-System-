"""
LangGraph Tutoring Workflow — Real State Graph for SapioCode

Implements a proper LangGraph StateGraph with:
  • Typed state (TypedDict) flowing through graph nodes
  • Conditional edges based on frustration, mastery, and AST analysis
  • Conversation memory persisted per student session
  • AST metadata flowing through every node
  • Frustration → gentle path / challenge path branching

Graph structure:
  ┌─────────┐     ┌──────────┐     ┌──────────────┐
  │ RECEIVE │ ──► │ ANALYZE  │ ──► │   ASSESS     │
  │ (input) │     │ (AST)    │     │ (mastery +   │
  └─────────┘     └──────────┘     │  frustration)│
                                    └──────┬───────┘
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                    ┌───────────┐   ┌───────────┐   ┌───────────┐
                    │  GENTLE   │   │  SOCRATIC │   │ CHALLENGE │
                    │  (high    │   │  (normal) │   │ (bored/   │
                    │  frust.)  │   │           │   │  high mst)│
                    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                          │               │               │
                          └───────────────┼───────────────┘
                                          ▼
                                    ┌───────────┐
                                    │  DELIVER  │
                                    │  (format  │
                                    │  + store) │
                                    └───────────┘
"""
from __future__ import annotations

from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from app.services.code_analyzer import CodeAnalyzer, CodeAnalysisResult
from app.services.ast_tutor import ASTTutor, ConversationTurn
from app.services.groq_service import get_groq_service
from app.services.bkt_local import get_local_bkt
from app.services.affect_adapter import get_affect_adapter
from app.services.session_store import (
    get_session_store, HintRecord, ConversationRecord,
)


# ══════════════════════════════════════════════════════════════
# STATE DEFINITION
# ══════════════════════════════════════════════════════════════

class TutoringState(TypedDict, total=False):
    """Typed state that flows through every node in the graph."""

    # ── Input (set by caller) ─────────────────────────────
    student_id: str
    problem_description: str
    code: str
    time_stuck: int
    previous_hints: int

    # ── Cognitive state (from affect adapter) ─────────────
    frustration: float
    engagement: float
    confusion: float
    boredom: float

    # ── AST analysis (set by analyze node) ────────────────
    analysis: Optional[CodeAnalysisResult]
    algorithm_pattern: str
    concepts_detected: List[str]
    issues: List[str]
    approach_summary: str

    # ── Mastery (set by assess node) ──────────────────────
    mastery_snapshot: Dict[str, float]
    avg_mastery: float

    # ── Hint generation (set by hint node) ────────────────
    hint_level: int
    hint_text: str
    hint_path: str  # "gentle" | "socratic" | "challenge"
    teaching_focus: str

    # ── Conversation memory ───────────────────────────────
    conversation_history: List[Dict[str, str]]

    # ── Output ────────────────────────────────────────────
    should_intervene: bool
    response: Dict[str, Any]


# ══════════════════════════════════════════════════════════════
# GRAPH NODES
# ══════════════════════════════════════════════════════════════

def receive_node(state: TutoringState) -> TutoringState:
    """
    Entry node — validates input and prepares initial state.
    Loads conversation history and current affect for the student.
    """
    student_id = state["student_id"]

    # Load current smoothed affect
    affect = get_affect_adapter()
    smoothed = affect.get_smoothed_state(student_id)

    return {
        **state,
        "frustration": state.get("frustration", smoothed.get("frustration", 0.1)),
        "engagement": state.get("engagement", smoothed.get("engagement", 0.7)),
        "confusion": state.get("confusion", smoothed.get("confusion", 0.2)),
        "boredom": state.get("boredom", smoothed.get("boredom", 0.0)),
        "conversation_history": _load_conversation(student_id),
    }


def analyze_node(state: TutoringState) -> TutoringState:
    """
    AST analysis node — runs deep code analysis.
    Extracts algorithm pattern, concepts, issues, function profiles.
    """
    analyzer = CodeAnalyzer()
    analysis = analyzer.analyze_python(state["code"])

    return {
        **state,
        "analysis": analysis,
        "algorithm_pattern": analysis.algorithm_pattern.value,
        "concepts_detected": analysis.concepts_detected,
        "issues": [loc.description for loc in analysis.issue_locations],
        "approach_summary": analysis.student_approach_summary,
    }


def assess_node(state: TutoringState) -> TutoringState:
    """
    Assessment node — checks mastery and decides if intervention needed.
    Combines BKT mastery + frustration + time_stuck.
    """
    student_id = state["student_id"]
    bkt = get_local_bkt()
    all_mastery = bkt.get_all_mastery(student_id)
    avg_mastery = (
        sum(all_mastery.values()) / len(all_mastery)
        if all_mastery else 0.5
    )

    # Intervention decision
    time_stuck = state.get("time_stuck", 0)
    frustration = state.get("frustration", 0.1)
    previous_hints = state.get("previous_hints", 0)

    should_intervene = (
        time_stuck > 30
        or frustration > 0.6
        or (time_stuck > 60 and frustration > 0.4)
        or previous_hints > 5
    )

    return {
        **state,
        "mastery_snapshot": all_mastery,
        "avg_mastery": avg_mastery,
        "should_intervene": should_intervene,
    }


async def gentle_hint_node(state: TutoringState) -> TutoringState:
    """
    Gentle path — high frustration detected.
    Uses empathetic tone, escalated hint level, sub-problem decomposition.
    """
    analysis = state.get("analysis")
    ast_tutor = ASTTutor()
    groq = get_groq_service()

    # Escalate hint level for frustrated students (more direct help)
    hint_level = min(state.get("previous_hints", 0) + 2, 4)

    ctx = ast_tutor.build_context(
        analysis, state["code"], state["problem_description"],
        state.get("conversation_history"),
    )
    prompt = ctx.to_llm_prompt(hint_level)

    # Prepend empathetic framing to system prompt
    system_prompt = (
        "You are SapioCode, a warm and patient Socratic tutor. "
        "The student is frustrated — be empathetic, encouraging, and gentle. "
        "Break the problem into a smaller sub-problem they can tackle first. "
        "Reference SPECIFIC elements from their code (function names, "
        "variable names, line numbers). "
        "Start with encouragement, then ask ONE focused question."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if state.get("conversation_history"):
        messages.extend(state["conversation_history"][-4:])
    messages.append({"role": "user", "content": prompt})

    hint_text = await groq.chat_completion(messages, temperature=0.7)
    hint_text = (
        "I can see this is challenging — take a breath! 😊\n\n"
        + hint_text
        + "\n\nRemember: struggling is part of learning. You're doing great!"
    )

    return {
        **state,
        "hint_level": hint_level,
        "hint_text": hint_text,
        "hint_path": "gentle",
        "teaching_focus": ctx.teaching_moment.focus_type,
    }


async def socratic_hint_node(state: TutoringState) -> TutoringState:
    """
    Socratic path — normal state.
    Standard Socratic questioning using full AST context.
    """
    analysis = state.get("analysis")
    ast_tutor = ASTTutor()
    groq = get_groq_service()

    hint_level = min(state.get("previous_hints", 0) + 1, 3)

    ctx = ast_tutor.build_context(
        analysis, state["code"], state["problem_description"],
        state.get("conversation_history"),
    )
    prompt = ctx.to_llm_prompt(hint_level)

    system_prompt = (
        "You are SapioCode, an intelligent Socratic coding tutor. "
        "You have deep AST analysis of the student's code. "
        "Always reference SPECIFIC elements (function names, variable names, "
        "line numbers). Never give generic advice."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if state.get("conversation_history"):
        messages.extend(state["conversation_history"][-4:])
    messages.append({"role": "user", "content": prompt})

    hint_text = await groq.chat_completion(messages, temperature=0.7)

    return {
        **state,
        "hint_level": hint_level,
        "hint_text": hint_text,
        "hint_path": "socratic",
        "teaching_focus": ctx.teaching_moment.focus_type,
    }


async def challenge_hint_node(state: TutoringState) -> TutoringState:
    """
    Challenge path — student is bored or has high mastery.
    Increase difficulty, ask deeper questions, suggest optimization.
    """
    analysis = state.get("analysis")
    ast_tutor = ASTTutor()
    groq = get_groq_service()

    hint_level = 1  # Keep Socratic (challenging)

    ctx = ast_tutor.build_context(
        analysis, state["code"], state["problem_description"],
        state.get("conversation_history"),
    )
    prompt = ctx.to_llm_prompt(hint_level)

    system_prompt = (
        "You are SapioCode, an intelligent tutor for an advanced student. "
        "The student seems comfortable — push them harder. "
        "Ask about time complexity, edge cases, or alternative approaches. "
        "Challenge them: 'Your solution works, but can you make it O(n)?' "
        "Reference their actual code structure from the AST analysis."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if state.get("conversation_history"):
        messages.extend(state["conversation_history"][-4:])
    messages.append({"role": "user", "content": prompt})

    hint_text = await groq.chat_completion(messages, temperature=0.8)
    hint_text = "Let's push further! 🚀\n\n" + hint_text

    return {
        **state,
        "hint_level": hint_level,
        "hint_text": hint_text,
        "hint_path": "challenge",
        "teaching_focus": ctx.teaching_moment.focus_type,
    }


def deliver_node(state: TutoringState) -> TutoringState:
    """
    Delivery node — formats final response and stores conversation turn.
    Persists to both in-memory store and SQLite for cross-restart durability.
    """
    student_id = state["student_id"]

    # Store this exchange in conversation memory (in-memory)
    _store_conversation_turn(student_id, ConversationTurn(
        role="tutor",
        content=state.get("hint_text", ""),
        hint_level=state.get("hint_level", 1),
        teaching_focus=state.get("teaching_focus", "general"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))

    # Persist hint to SQLite (best-effort)
    try:
        store = get_session_store()
        if state.get("hint_text"):
            store.record_hint(HintRecord(
                student_id=student_id,
                session_id=f"{student_id}_langgraph",
                hint_text=state.get("hint_text", ""),
                hint_level=state.get("hint_level", 1),
                hint_path=state.get("hint_path", "socratic"),
                teaching_focus=state.get("teaching_focus", ""),
                frustration_at_time=state.get("frustration", 0.0),
                mastery_at_time=state.get("avg_mastery", 0.5),
            ))
    except Exception:
        pass  # Don't break pipeline if SQLite fails

    response = {
        "student_id": student_id,
        "should_intervene": state.get("should_intervene", False),
        "hint": state.get("hint_text", ""),
        "hint_level": state.get("hint_level", 1),
        "hint_path": state.get("hint_path", "socratic"),
        "teaching_focus": state.get("teaching_focus", ""),
        "algorithm_pattern": state.get("algorithm_pattern", "unknown"),
        "concepts_detected": state.get("concepts_detected", []),
        "issues_found": state.get("issues", []),
        "approach_summary": state.get("approach_summary", ""),
        "mastery_snapshot": state.get("mastery_snapshot", {}),
        "avg_mastery": state.get("avg_mastery", 0.5),
        "cognitive_state": {
            "frustration": state.get("frustration", 0.0),
            "engagement": state.get("engagement", 0.5),
            "confusion": state.get("confusion", 0.0),
            "boredom": state.get("boredom", 0.0),
        },
    }

    return {**state, "response": response}


# ══════════════════════════════════════════════════════════════
# CONDITIONAL EDGES
# ══════════════════════════════════════════════════════════════

def route_by_affect(state: TutoringState) -> Literal["gentle", "socratic", "challenge"]:
    """
    Conditional edge: choose hint path based on affect + mastery.

    High frustration (>0.7)                        → gentle
    Low frustration + high mastery (>0.7) or bored → challenge
    Otherwise                                      → socratic (default)
    """
    frustration = state.get("frustration", 0.1)
    boredom = state.get("boredom", 0.0)
    engagement = state.get("engagement", 0.5)
    avg_mastery = state.get("avg_mastery", 0.5)

    if frustration > 0.7:
        return "gentle"
    if (avg_mastery > 0.7 and frustration < 0.3) or (boredom > 0.6 and engagement < 0.3):
        return "challenge"
    return "socratic"


# ══════════════════════════════════════════════════════════════
# CONVERSATION MEMORY (per-student, in-process)
# ══════════════════════════════════════════════════════════════

_conversation_store: Dict[str, List[ConversationTurn]] = {}
MAX_MEMORY_TURNS = 20


def _load_conversation(student_id: str) -> List[Dict[str, str]]:
    """Load recent conversation as OpenAI-format message list."""
    turns = _conversation_store.get(student_id, [])[-6:]
    return [
        {"role": t.role if t.role != "tutor" else "assistant", "content": t.content}
        for t in turns
    ]


def _store_conversation_turn(student_id: str, turn: ConversationTurn) -> None:
    """Append a turn to in-memory store and persist to SQLite."""
    if student_id not in _conversation_store:
        _conversation_store[student_id] = []
    _conversation_store[student_id].append(turn)
    if len(_conversation_store[student_id]) > MAX_MEMORY_TURNS:
        _conversation_store[student_id] = _conversation_store[student_id][-MAX_MEMORY_TURNS:]

    # Persist to SQLite (best-effort)
    try:
        store = get_session_store()
        store.record_conversation_turn(ConversationRecord(
            student_id=student_id,
            role=turn.role,
            content=turn.content,
            hint_level=turn.hint_level,
            teaching_focus=turn.teaching_focus,
            timestamp=turn.timestamp,
        ))
    except Exception:
        pass


def record_student_message(student_id: str, message: str) -> None:
    """Record student's code/message into conversation memory."""
    _store_conversation_turn(student_id, ConversationTurn(
        role="student",
        content=message,
        hint_level=0,
        teaching_focus="",
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))


def get_conversation_history(student_id: str) -> List[Dict[str, str]]:
    """Public accessor for conversation history."""
    return _load_conversation(student_id)


def clear_conversation(student_id: str) -> None:
    """Clear conversation history for a student."""
    _conversation_store.pop(student_id, None)


# ══════════════════════════════════════════════════════════════
# BUILD THE GRAPH
# ══════════════════════════════════════════════════════════════

def _combined_route(state: TutoringState) -> str:
    """
    Combined routing function for assess node.
    First checks if intervention is needed, then routes by affect.
    """
    if not state.get("should_intervene", False):
        return "deliver"
    return route_by_affect(state)


def build_tutoring_graph():
    """
    Construct and compile the LangGraph tutoring workflow.

    Returns a compiled StateGraph that can be invoked with:
        result = await graph.ainvoke(initial_state)
    """
    graph = StateGraph(TutoringState)

    # ── Add all nodes ──
    graph.add_node("receive", receive_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("assess", assess_node)
    graph.add_node("gentle", gentle_hint_node)
    graph.add_node("socratic", socratic_hint_node)
    graph.add_node("challenge", challenge_hint_node)
    graph.add_node("deliver", deliver_node)

    # ── Set entry point ──
    graph.set_entry_point("receive")

    # ── Linear edges ──
    graph.add_edge("receive", "analyze")
    graph.add_edge("analyze", "assess")

    # ── Conditional: assess → gentle / socratic / challenge / deliver ──
    # Single combined conditional edge handles both intervention check
    # and affect-based routing in one step.
    graph.add_conditional_edges(
        "assess",
        _combined_route,
        {
            "gentle": "gentle",
            "socratic": "socratic",
            "challenge": "challenge",
            "deliver": "deliver",
        },
    )

    # ── All hint paths converge to deliver ──
    graph.add_edge("gentle", "deliver")
    graph.add_edge("socratic", "deliver")
    graph.add_edge("challenge", "deliver")

    # ── Deliver → END ──
    graph.add_edge("deliver", END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_compiled_graph = None


def get_tutoring_graph():
    """Get or build the compiled tutoring graph singleton."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_tutoring_graph()
    return _compiled_graph
