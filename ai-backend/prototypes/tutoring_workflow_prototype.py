"""
LangGraph Prototype: Adaptive Tutoring Workflow

This is a simplified prototype demonstrating how LangGraph can orchestrate
the SapioCode tutoring system with stateful, adaptive behavior.

Run this to see how the workflow adapts based on student progress.
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END, add_messages
import json


# ============================================================================
# STATE DEFINITION
# ============================================================================

class TutoringState(TypedDict):
    """
    State that flows through the tutoring workflow.
    This represents the 'memory' of the tutoring session.
    """
    # Student context
    student_id: str
    problem_description: str
    current_code: str
    
    # Conversation history
    messages: Annotated[list, add_messages]
    
    # Tutoring state
    hint_level: int  # 0=Socratic, 1=Conceptual, 2=Pseudocode, 3=Direct
    attempts: int
    time_stuck_minutes: int
    
    # Analysis results
    has_syntax_error: bool
    has_logic_error: bool
    complexity_score: int
    
    # Decision flags
    should_escalate: bool
    is_solved: bool


# ============================================================================
# NODE FUNCTIONS (These would call your actual services)
# ============================================================================

def analyze_code_node(state: TutoringState) -> dict:
    """
    Node: Analyze student's code
    In production, this would call your CodeAnalyzer service
    """
    code = state["current_code"]
    
    # Simulate analysis (in production, use your CodeAnalyzer)
    has_syntax = "def" not in code  # Simplified check
    has_logic = "return" not in code  # Simplified check
    complexity = len(code.split("\n"))
    
    print(f"📊 [ANALYZE] Code has {complexity} lines")
    
    return {
        "has_syntax_error": has_syntax,
        "has_logic_error": has_logic,
        "complexity_score": complexity,
        "messages": [{
            "role": "system",
            "content": f"Analysis: syntax_ok={not has_syntax}, logic_ok={not has_logic}"
        }]
    }


def check_progress_node(state: TutoringState) -> dict:
    """
    Node: Evaluate if student is making progress
    """
    attempts = state["attempts"]
    has_errors = state["has_syntax_error"] or state["has_logic_error"]
    
    # Decision logic
    if attempts > 3 and has_errors:
        should_escalate = True
        print(f"⚠️  [PROGRESS] Student stuck after {attempts} attempts - escalating")
    elif not has_errors:
        should_escalate = False
        print(f"✅ [PROGRESS] Student making progress!")
    else:
        should_escalate = False
        print(f"🔄 [PROGRESS] Student trying... ({attempts} attempts)")
    
    return {
        "should_escalate": should_escalate,
        "is_solved": not has_errors
    }


def generate_hint_node(state: TutoringState) -> dict:
    """
    Node: Generate adaptive hint based on current state
    In production, this would call your HintGenerator service
    """
    level = state["hint_level"]
    problem = state["problem_description"]
    
    # Simulate hint generation (in production, use your HintGenerator + Groq)
    hints = {
        0: f"🤔 Socratic: What is the first step to solve '{problem}'?",
        1: f"💡 Conceptual: Think about using a loop to iterate...",
        2: f"📝 Pseudocode: Try: for item in list: if condition: return item",
        3: f"🎯 Direct: Here's the solution: def solve(): return [x for x in range(10)]"
    }
    
    hint = hints.get(level, hints[3])
    new_level = min(level + 1, 3)  # Escalate, max at 3
    
    print(f"💬 [HINT] Level {level} → {new_level}: {hint[:50]}...")
    
    return {
        "messages": [{"role": "assistant", "content": hint}],
        "hint_level": new_level
    }


def encourage_node(state: TutoringState) -> dict:
    """
    Node: Provide encouragement when student is on the right track
    """
    print(f"🎉 [ENCOURAGE] Great job! Keep going!")
    
    return {
        "messages": [{
            "role": "assistant",
            "content": "You're on the right track! Keep refining your solution."
        }]
    }


def celebrate_node(state: TutoringState) -> dict:
    """
    Node: Celebrate when problem is solved
    """
    print(f"🏆 [CELEBRATE] Problem solved!")
    
    return {
        "messages": [{
            "role": "assistant",
            "content": "Excellent work! You've solved the problem. Ready for the next challenge?"
        }],
        "is_solved": True
    }


# ============================================================================
# CONDITIONAL EDGE FUNCTIONS (Decision Logic)
# ============================================================================

def route_after_progress_check(state: TutoringState) -> Literal["solved", "needs_help", "encourage"]:
    """
    Decide what to do after checking progress
    """
    if state["is_solved"]:
        return "solved"
    elif state["should_escalate"]:
        return "needs_help"
    else:
        return "encourage"


# ============================================================================
# BUILD THE WORKFLOW GRAPH
# ============================================================================

def create_tutoring_workflow():
    """
    Create the LangGraph workflow for adaptive tutoring
    """
    # Initialize graph with our state
    workflow = StateGraph(TutoringState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_code_node)
    workflow.add_node("check_progress", check_progress_node)
    workflow.add_node("hint", generate_hint_node)
    workflow.add_node("encourage", encourage_node)
    workflow.add_node("celebrate", celebrate_node)
    
    # Define flow
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "check_progress")
    
    # Conditional routing after progress check
    workflow.add_conditional_edges(
        "check_progress",
        route_after_progress_check,
        {
            "solved": "celebrate",
            "needs_help": "hint",
            "encourage": "encourage"
        }
    )
    
    # All paths lead to END
    workflow.add_edge("hint", END)
    workflow.add_edge("encourage", END)
    workflow.add_edge("celebrate", END)
    
    # Compile the graph
    return workflow.compile()


# ============================================================================
# TEST THE WORKFLOW
# ============================================================================

def test_workflow():
    """
    Test the tutoring workflow with different scenarios
    """
    print("\n" + "="*70)
    print("🧪 TESTING ADAPTIVE TUTORING WORKFLOW")
    print("="*70 + "\n")
    
    app = create_tutoring_workflow()
    
    # Scenario 1: Student stuck (needs escalating hints)
    print("\n📚 SCENARIO 1: Student Stuck (Bad Code)")
    print("-" * 70)
    
    initial_state = {
        "student_id": "alice_001",
        "problem_description": "Write a function to find even numbers",
        "current_code": "x = 5\nprint(x)",  # Bad code
        "messages": [],
        "hint_level": 0,
        "attempts": 4,  # Many attempts
        "time_stuck_minutes": 15,
        "has_syntax_error": False,
        "has_logic_error": False,
        "complexity_score": 0,
        "should_escalate": False,
        "is_solved": False
    }
    
    result = app.invoke(initial_state)
    print(f"\n📤 Final State:")
    print(f"   Hint Level: {result['hint_level']}")
    print(f"   Solved: {result['is_solved']}")
    print(f"   Last Message: {result['messages'][-1]['content'][:60]}...")
    
    # Scenario 2: Student making progress
    print("\n\n📚 SCENARIO 2: Student Making Progress (Good Code)")
    print("-" * 70)
    
    progress_state = {
        "student_id": "bob_002",
        "problem_description": "Write a function to find even numbers",
        "current_code": "def find_evens(nums):\n    return [x for x in nums if x % 2 == 0]",
        "messages": [],
        "hint_level": 1,
        "attempts": 2,
        "time_stuck_minutes": 5,
        "has_syntax_error": False,
        "has_logic_error": False,
        "complexity_score": 0,
        "should_escalate": False,
        "is_solved": False
    }
    
    result = app.invoke(progress_state)
    print(f"\n📤 Final State:")
    print(f"   Hint Level: {result['hint_level']}")
    print(f"   Solved: {result['is_solved']}")
    print(f"   Last Message: {result['messages'][-1]['content'][:60]}...")
    
    print("\n" + "="*70)
    print("✅ WORKFLOW TEST COMPLETE")
    print("="*70 + "\n")


# ============================================================================
# VISUALIZATION (Optional - requires graphviz)
# ============================================================================

def visualize_workflow():
    """
    Generate a visual representation of the workflow
    Requires: pip install pygraphviz (optional)
    """
    try:
        from IPython.display import Image, display
        
        app = create_tutoring_workflow()
        display(Image(app.get_graph().draw_mermaid_png()))
        print("✅ Workflow visualization generated!")
    except ImportError:
        print("⚠️  Visualization requires pygraphviz. Skipping...")
        print("   Install with: pip install pygraphviz")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  LangGraph Prototype: Adaptive Tutoring Workflow             ║
    ║  SapioCode AI Backend - Role 2 (AI Engineer)                 ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    test_workflow()
    
    print("\n💡 Next Steps:")
    print("   1. Study how the workflow adapts based on state")
    print("   2. Replace mock functions with your actual services")
    print("   3. Add checkpointing for persistent sessions")
    print("   4. Integrate with your FastAPI endpoints")
    print("\n")
