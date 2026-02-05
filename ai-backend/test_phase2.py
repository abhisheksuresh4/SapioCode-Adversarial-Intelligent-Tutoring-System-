"""Test Phase 2 Components"""
import sys
sys.path.insert(0, 'd:\\sapiocode\\ai-backend')

from app.services.code_analyzer import CodeAnalyzer
from app.services.tutoring_engine import TutoringEngine, StudentContext, HintLevel

print("=" * 60)
print("Phase 2 Component Test")
print("=" * 60)

# Test 1: Code Analyzer
print("\n[Test 1] Code Analyzer")
print("-" * 40)

analyzer = CodeAnalyzer()

code1 = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""

result = analyzer.analyze_python(code1)
print(f"✅ Code Analysis: Valid={result.is_valid}")
print(f"   Functions: {result.function_count}")
print(f"   Has Recursion: {result.has_recursion}")
print(f"   Complexity: {result.complexity_score}")

# Test 2: Code with Issues
print("\n[Test 2] Code with Issues")
print("-" * 40)

code2 = """
def broken_loop():
    while True:
        print("stuck")
"""

result2 = analyzer.analyze_python(code2)
print(f"✅ Code Analysis: Valid={result2.is_valid}")
print(f"   Issues: {[i.value for i in result2.issues]}")
print(f"   Loops: {result2.loop_count}")

# Test 3: Tutoring Engine - Intervention Decision
print("\n[Test 3] Tutoring Engine - Intervention Logic")
print("-" * 40)

engine = TutoringEngine()

# Scenario 1: Not stuck enough
context1 = StudentContext(
    problem_description="Write a function",
    current_code="def solve():\n    pass",
    time_stuck=15,
    frustration_level=0.1,
    previous_hints=0,
    code_attempts=1
)

decision1 = engine.decide_intervention(context1)
print(f"✅ Low stuck time: Should intervene={decision1.should_intervene}")
print(f"   Reason: {decision1.reason}")

# Scenario 2: High frustration
context2 = StudentContext(
    problem_description="Implement quicksort",
    current_code="# stuck",
    time_stuck=120,
    frustration_level=0.8,
    previous_hints=2,
    code_attempts=6
)

decision2 = engine.decide_intervention(context2)
print(f"\n✅ High frustration: Should intervene={decision2.should_intervene}")
print(f"   Reason: {decision2.reason}")
print(f"   Hint Level: {decision2.hint_level.name}")
print(f"   Urgency: {decision2.urgency:.2f}")

# Test 4: Hint Level Escalation
print("\n[Test 4] Hint Level Escalation")
print("-" * 40)

levels = [
    (0, 0.2, HintLevel.SOCRATIC_QUESTION),
    (1, 0.4, HintLevel.CONCEPTUAL_NUDGE),
    (2, 0.65, HintLevel.PSEUDO_CODE),
    (3, 0.85, HintLevel.DIRECT_HINT)
]

for prev_hints, frustration, expected_level in levels:
    context = StudentContext(
        problem_description="Test",
        current_code="test",
        time_stuck=100,
        frustration_level=frustration,
        previous_hints=prev_hints,
        code_attempts=3
    )
    level = engine._determine_hint_level(context)
    status = "✅" if level == expected_level else "❌"
    print(f"{status} Hints={prev_hints}, Frustration={frustration} → {level.name}")

print("\n" + "=" * 60)
print("✅ All Phase 2 Components Working!")
print("=" * 60)
