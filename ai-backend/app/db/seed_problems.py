"""
Seed Problem Bank for SapioCode
8 starter problems mapped to curriculum concepts: variables → sorting
"""
from typing import List, Dict, Any


def get_seed_problems() -> List[Dict[str, Any]]:
    """Return the starter problem bank"""
    return [
        # ─── Variables & Types ─────────────────────────────
        {
            "id": "variables_01",
            "title": "Temperature Converter",
            "description": (
                "Write a function `convert_temp(celsius)` that takes a temperature "
                "in Celsius and returns it in Fahrenheit.\n\n"
                "Formula: F = (C × 9/5) + 32\n\n"
                "Example:\n  convert_temp(0) → 32.0\n  convert_temp(100) → 212.0"
            ),
            "difficulty": "easy",
            "concepts": ["variables"],
            "graph_node_id": "variables",
            "prerequisites": [],
            "starter_code": "def convert_temp(celsius):\n    # Your code here\n    pass",
            "solution_template": "# Step 1: Apply F = (C * 9/5) + 32\n# Step 2: Return result",
            "test_cases": [
                {"input": "0", "expected_output": "32.0", "explanation": "Freezing point", "is_hidden": False},
                {"input": "100", "expected_output": "212.0", "explanation": "Boiling point", "is_hidden": False},
                {"input": "-40", "expected_output": "-40.0", "explanation": "Same in both scales", "is_hidden": True},
                {"input": "37", "expected_output": "98.6", "explanation": "Body temperature", "is_hidden": True},
            ],
            "hints": [
                "What mathematical operation converts between the two scales?",
                "Think about the relationship: multiply, then add.",
                "The formula is F = (C × 9/5) + 32. Apply it directly."
            ]
        },

        # ─── Conditionals ─────────────────────────────────
        {
            "id": "conditionals_01",
            "title": "Grade Calculator",
            "description": (
                "Write a function `get_grade(score)` that returns the letter grade:\n\n"
                "  90-100 → 'A'\n  80-89 → 'B'\n  70-79 → 'C'\n"
                "  60-69 → 'D'\n  Below 60 → 'F'\n\n"
                "Example:\n  get_grade(95) → 'A'\n  get_grade(73) → 'C'"
            ),
            "difficulty": "easy",
            "concepts": ["conditionals"],
            "graph_node_id": "conditionals",
            "prerequisites": ["variables"],
            "starter_code": "def get_grade(score):\n    # Your code here\n    pass",
            "solution_template": "# Use if/elif/else to check score ranges",
            "test_cases": [
                {"input": "95", "expected_output": "A", "explanation": "High A", "is_hidden": False},
                {"input": "85", "expected_output": "B", "explanation": "Mid B", "is_hidden": False},
                {"input": "73", "expected_output": "C", "explanation": "Low C", "is_hidden": False},
                {"input": "60", "expected_output": "D", "explanation": "Border D", "is_hidden": True},
                {"input": "59", "expected_output": "F", "explanation": "Just below D", "is_hidden": True},
            ],
            "hints": [
                "How many different ranges do you need to check?",
                "Start from the highest range and work down using if/elif.",
                "Check score >= 90 first, then >= 80, etc."
            ]
        },

        # ─── Loops ─────────────────────────────────────────
        {
            "id": "loops_01",
            "title": "Sum of Digits",
            "description": (
                "Write a function `sum_digits(n)` that returns the sum of all digits "
                "of a non-negative integer.\n\n"
                "Example:\n  sum_digits(123) → 6\n  sum_digits(9999) → 36"
            ),
            "difficulty": "easy",
            "concepts": ["loops"],
            "graph_node_id": "loops",
            "prerequisites": ["conditionals"],
            "starter_code": "def sum_digits(n):\n    # Your code here\n    pass",
            "solution_template": "# Use while loop: extract last digit with % 10, remove with // 10",
            "test_cases": [
                {"input": "123", "expected_output": "6", "explanation": "1+2+3", "is_hidden": False},
                {"input": "9999", "expected_output": "36", "explanation": "9+9+9+9", "is_hidden": False},
                {"input": "0", "expected_output": "0", "explanation": "Edge: zero", "is_hidden": True},
                {"input": "5", "expected_output": "5", "explanation": "Single digit", "is_hidden": True},
            ],
            "hints": [
                "How can you extract the last digit of a number?",
                "n % 10 gives the last digit. n // 10 removes it.",
                "Loop while n > 0: add n % 10 to sum, then n = n // 10."
            ]
        },

        # ─── Functions ─────────────────────────────────────
        {
            "id": "functions_01",
            "title": "Power Function",
            "description": (
                "Write a function `power(base, exp)` that calculates base^exp "
                "WITHOUT using ** or pow().\n\n"
                "Example:\n  power(2, 10) → 1024\n  power(3, 0) → 1"
            ),
            "difficulty": "medium",
            "concepts": ["functions", "loops"],
            "graph_node_id": "functions",
            "prerequisites": ["loops"],
            "starter_code": "def power(base, exp):\n    # Do NOT use ** or pow()\n    pass",
            "solution_template": "# Handle exp=0. Loop exp times, multiply result *= base.",
            "test_cases": [
                {"input": "2, 10", "expected_output": "1024", "explanation": "2^10", "is_hidden": False},
                {"input": "3, 0", "expected_output": "1", "explanation": "Anything^0 = 1", "is_hidden": False},
                {"input": "5, 3", "expected_output": "125", "explanation": "5^3", "is_hidden": True},
                {"input": "1, 100", "expected_output": "1", "explanation": "1^anything = 1", "is_hidden": True},
            ],
            "hints": [
                "What does it mean to raise a number to a power?",
                "Repeated multiplication. What kind of loop does that?",
                "result=1, loop exp times, result *= base each time."
            ]
        },

        # ─── Arrays ────────────────────────────────────────
        {
            "id": "arrays_01",
            "title": "Two Sum",
            "description": (
                "Write a function `two_sum(nums, target)` that returns indices of "
                "two numbers adding to target.\n\n"
                "Each input has exactly one solution. Don't use the same element twice.\n\n"
                "Example:\n  two_sum([2,7,11,15], 9) → [0, 1]"
            ),
            "difficulty": "medium",
            "concepts": ["arrays"],
            "graph_node_id": "arrays",
            "prerequisites": ["loops"],
            "starter_code": "def two_sum(nums, target):\n    # Your code here\n    pass",
            "solution_template": "# Use a dict to store seen numbers. Check if complement exists.",
            "test_cases": [
                {"input": "[2,7,11,15], 9", "expected_output": "[0, 1]", "explanation": "2+7=9", "is_hidden": False},
                {"input": "[3,2,4], 6", "expected_output": "[1, 2]", "explanation": "2+4=6", "is_hidden": False},
                {"input": "[3,3], 6", "expected_output": "[0, 1]", "explanation": "Duplicates", "is_hidden": True},
            ],
            "hints": [
                "For each number, what other number would you need?",
                "That's called the complement: target - current.",
                "Use a dictionary to store {number: index}. O(n) solution."
            ]
        },

        # ─── Recursion ─────────────────────────────────────
        {
            "id": "recursion_01",
            "title": "Fibonacci",
            "description": (
                "Write a function `fibonacci(n)` returning the nth Fibonacci number.\n\n"
                "F(0)=0, F(1)=1, F(n) = F(n-1) + F(n-2)\n\n"
                "Example:\n  fibonacci(0) → 0\n  fibonacci(6) → 8"
            ),
            "difficulty": "hard",
            "concepts": ["recursion"],
            "graph_node_id": "recursion",
            "prerequisites": ["functions"],
            "starter_code": "def fibonacci(n):\n    # Your code here\n    pass",
            "solution_template": "# Base: n=0→0, n=1→1. Recursive: fib(n-1) + fib(n-2)",
            "test_cases": [
                {"input": "0", "expected_output": "0", "explanation": "Base case", "is_hidden": False},
                {"input": "1", "expected_output": "1", "explanation": "Base case", "is_hidden": False},
                {"input": "6", "expected_output": "8", "explanation": "0,1,1,2,3,5,8", "is_hidden": False},
                {"input": "10", "expected_output": "55", "explanation": "Larger input", "is_hidden": True},
            ],
            "hints": [
                "Every recursive function needs a base case. What are the simplest inputs?",
                "F(0)=0, F(1)=1 are base cases. How is F(n) expressed in terms of smaller F?",
                "return fibonacci(n-1) + fibonacci(n-2) for n >= 2."
            ]
        },

        # ─── Linked Lists ─────────────────────────────────
        {
            "id": "linked_lists_01",
            "title": "Reverse Linked List",
            "description": (
                "Write a function `reverse_list(head)` that reverses a singly linked list.\n\n"
                "Example:\n  1→2→3→4 becomes 4→3→2→1"
            ),
            "difficulty": "hard",
            "concepts": ["linked_lists"],
            "graph_node_id": "linked_lists",
            "prerequisites": ["arrays", "recursion"],
            "starter_code": (
                "class ListNode:\n    def __init__(self, val=0, next=None):\n"
                "        self.val = val\n        self.next = next\n\n"
                "def reverse_list(head):\n    # Your code here\n    pass"
            ),
            "solution_template": "# Three pointers: prev, current, next_node. Reverse each link.",
            "test_cases": [
                {"input": "[1,2,3,4]", "expected_output": "[4,3,2,1]", "explanation": "Normal", "is_hidden": False},
                {"input": "[1]", "expected_output": "[1]", "explanation": "Single node", "is_hidden": True},
                {"input": "[]", "expected_output": "[]", "explanation": "Empty list", "is_hidden": True},
            ],
            "hints": [
                "What if you changed where each node's 'next' points?",
                "You need a 'prev' variable to remember the previous node.",
                "prev=None, current=head. Each step: save next, reverse link, advance."
            ]
        },

        # ─── Sorting ──────────────────────────────────────
        {
            "id": "sorting_01",
            "title": "Merge Sort",
            "description": (
                "Implement `merge_sort(arr)` using the merge sort algorithm.\n\n"
                "Example:\n  merge_sort([38,27,43,3,9,82,10]) → [3,9,10,27,38,43,82]"
            ),
            "difficulty": "hard",
            "concepts": ["sorting", "recursion"],
            "graph_node_id": "sorting",
            "prerequisites": ["arrays", "recursion"],
            "starter_code": "def merge_sort(arr):\n    # Your code here\n    pass",
            "solution_template": "# Split in half, sort each, merge sorted halves",
            "test_cases": [
                {"input": "[38,27,43,3,9,82,10]", "expected_output": "[3, 9, 10, 27, 38, 43, 82]", "explanation": "Normal", "is_hidden": False},
                {"input": "[1]", "expected_output": "[1]", "explanation": "Single element", "is_hidden": True},
                {"input": "[]", "expected_output": "[]", "explanation": "Empty", "is_hidden": True},
            ],
            "hints": [
                "Divide and conquer: how do you split an array in half?",
                "arr[:mid] and arr[mid:]. Recursively sort each half.",
                "Merge step: compare elements from both halves, pick smaller."
            ]
        },
    ]
