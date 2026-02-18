"""Quick manual test for Problem Generator - Run without pytest"""
import asyncio
from app.services.problem_generator import get_problem_generator


async def quick_test():
    """Quick validation test"""
    print("\n" + "="*60)
    print("🧪 PROBLEM GENERATOR - QUICK VALIDATION TEST")
    print("="*60)
    
    generator = get_problem_generator()
    
    # Test 1: Simple problem
    print("\n📝 Test 1: Generate Simple Problem")
    print("-" * 60)
    
    try:
        spec = await generator.generate_problem_from_text(
            raw_description="Write a function that returns the sum of two numbers",
            language="python",
            difficulty="easy",
            num_test_cases=3
        )
        
        print(f"✅ Title: {spec.title}")
        print(f"✅ Difficulty: {spec.difficulty}")
        print(f"✅ Test Cases: {len(spec.test_cases)}")
        print(f"✅ Hints: {len(spec.hints)}")
        print(f"✅ Concepts: {', '.join(spec.concepts[:3])}")
        print(f"\n💻 Starter Code:\n{spec.starter_code[:100]}...")
        
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")
        return
    
    # Test 2: Additional test cases
    print("\n\n📝 Test 2: Generate Additional Test Cases")
    print("-" * 60)
    
    try:
        additional = await generator.generate_additional_test_cases(
            problem_description=spec.description,
            existing_test_cases=spec.test_cases,
            num_additional=2
        )
        
        print(f"✅ Generated {len(additional)} additional test cases")
        print(f"✅ All marked as hidden: {all(tc.is_hidden for tc in additional)}")
        
    except Exception as e:
        print(f"❌ Test 2 Failed: {e}")
        return
    
    print("\n" + "="*60)
    print("✨ ALL TESTS PASSED - Problem Generator is working!")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting Quick Validation...")
    asyncio.run(quick_test())
