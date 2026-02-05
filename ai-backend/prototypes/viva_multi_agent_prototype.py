"""
Multi-Agent Viva Voce Prototype
------------------------------
Demonstrates a multi-agent orchestration for oral examinations using LangGraph.

Agents:
1. Examiner: Generates tough questions based on code.
2. Advocate: Intervenes if the student struggles, rephrasing or giving hints.
3. Grader: Evaluates the final answer and assigns a score.

Flow:
Examiner -> Student Matches? -> Grader
                |
           Student Stuck?
                |
             Advocate -> Examiner (Rephrase)
"""

from typing import TypedDict, Annotated, List, Literal, Union, Dict
from langgraph.graph import StateGraph, END, add_messages
import random

# ============================================================================
# STATE DEFINITION
# ============================================================================

class VivaState(TypedDict):
    """Shared state for the Viva exam session"""
    student_id: str
    code_context: str
    
    # Conversation
    messages: Annotated[list, add_messages]
    
    # Exam State
    current_question: str
    difficulty: str  # "hard", "medium", "easy"
    attempt_count: int
    is_stuck: bool
    
    # Grading
    scores: List[int]
    final_verdict: str

# ============================================================================
# AGENT NODES
# ============================================================================

def examiner_agent(state: VivaState) -> Dict:
    """
    The Examiner: Asks questions based on code and difficulty.
    """
    difficulty = state.get("difficulty", "hard")
    code = state["code_context"]
    
    # Simulate LLM generation
    questions = {
        "hard": f"Constructively critique the time complexity of your 'code' function.",
        "medium": f"Can you explain how this loop in 'code' works?",
        "easy": f"What does this specific line on line 2 do?"
    }
    
    question = questions.get(difficulty, questions["medium"])
    
    print(f"🧐 [EXAMINER] ({difficulty}): {question}")
    
    return {
        "current_question": question,
        "messages": [{"role": "assistant", "name": "Examiner", "content": question}]
    }

def advocate_agent(state: VivaState) -> Dict:
    """
    The Advocate: Helps the student if they are stuck.
    Lowers difficulty or rephrases.
    """
    print(f"🛡️ [ADVOCATE] Student is stuck. Requesting easier question.")
    
    return {
        "difficulty": "medium" if state["difficulty"] == "hard" else "easy",
        "is_stuck": False,  # Reset stuck flag
        "messages": [{"role": "assistant", "name": "Advocate", "content": "Let's try a simpler angle..."}]
    }

def grader_agent(state: VivaState) -> Dict:
    """
    The Grader: Evaluates the answer derived from the conversation.
    """
    # Simulate grading the last student response
    # In reality, this would analyze state['messages']
    
    score = random.randint(70, 100)
    print(f"📝 [GRADER] Answer acceptable. Score: {score}")
    
    return {
        "scores": state.get("scores", []) + [score],
        "final_verdict": "pass"
    }

# ============================================================================
# LOGIC / EDGES
# ============================================================================

def check_student_response(state: VivaState) -> Literal["grade", "advocate", "continue"]:
    """
    Simulates checking the student's answer.
    """
    # Simulate input (in real app, this waits for user input)
    # We'll randomize for the prototype demo
    
    action = random.choice(["answer_good", "stuck"])
    
    if action == "answer_good":
        return "grade"
    else:
        # If stuck, did we already try helping?
        if state["difficulty"] == "easy":
            return "grade" # Give up and grade what we have
        return "advocate"

# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_viva_graph():
    workflow = StateGraph(VivaState)
    
    # Add Nodes
    workflow.add_node("examiner", examiner_agent)
    workflow.add_node("advocate", advocate_agent)
    workflow.add_node("grader", grader_agent)
    
    # Add Edges
    workflow.set_entry_point("examiner")
    
    workflow.add_conditional_edges(
        "examiner",
        check_student_response,
        {
            "grade": "grader",
            "advocate": "advocate",
            "continue": "examiner"
        }
    )
    
    workflow.add_edge("advocate", "examiner") # Advocate asks Examiner to try again
    workflow.add_edge("grader", END)
    
    return workflow.compile()

# ============================================================================
# SIMULATION
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Multi-Agent Viva Simulation...")
    
    graph = create_viva_graph()
    
    initial_state = {
        "student_id": "student_123",
        "code_context": "def fib(n): return fib(n-1) + fib(n-2)",
        "difficulty": "hard",
        "attempt_count": 0,
        "is_stuck": False,
        "messages": []
    }
    
    # Run the graph
    for event in graph.stream(initial_state):
        pass
        
    print("\n✅ Simulation Complete.")
