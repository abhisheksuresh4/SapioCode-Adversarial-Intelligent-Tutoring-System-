"""
Code Analysis Module — Deep AST analysis for Neuro-Symbolic tutoring.

This is the "symbolic" half of the NS-CITS architecture.
It extracts structural reasoning from the student's code so the LLM
can generate code-SPECIFIC Socratic hints rather than generic ones.

E.g. instead of: "Think about your loop condition"
     it enables:  "Your while loop on line 8 uses `i < len(arr)` —
                   what happens when `arr` is empty?"
"""
import ast
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CodeIssue(Enum):
    """Types of issues detected in code"""
    SYNTAX_ERROR = "syntax_error"
    INFINITE_LOOP = "infinite_loop"
    MISSING_RETURN = "missing_return"
    UNUSED_VARIABLE = "unused_variable"
    NO_TERMINATION = "no_termination"
    EMPTY_FUNCTION = "empty_function"
    MISSING_BASE_CASE = "missing_base_case"
    WRONG_RETURN_TYPE = "wrong_return_type"
    OFF_BY_ONE = "off_by_one"
    SHADOWED_VARIABLE = "shadowed_variable"
    WRONG_ALGORITHM = "wrong_algorithm"           # Suboptimal algorithm choice
    INEFFICIENT_SOLUTION = "inefficient_solution"  # Correct but O(n²+) when better exists


class AlgorithmPattern(Enum):
    """
    High-level algorithm pattern detected from AST structure.
    Used to generate pattern-specific Socratic questions.
    """
    RECURSIVE         = "recursive"        # Function calls itself
    ITERATIVE         = "iterative"        # Loop-based traversal
    DIVIDE_CONQUER    = "divide_conquer"   # Recursive halving (binary search, merge sort)
    DYNAMIC_PROG      = "dp"               # Memoization dict or 2D table
    TWO_POINTER       = "two_pointer"      # Two index vars moving through array
    SLIDING_WINDOW    = "sliding_window"   # Window that shifts through sequence
    BFS_DFS           = "bfs_dfs"          # Explicit queue/stack traversal
    BRUTE_FORCE       = "brute_force"      # Nested loops, O(n²+)
    UNKNOWN           = "unknown"


@dataclass
class IssueLocation:
    """A specific issue with its exact location in code"""
    issue_type: CodeIssue
    line: Optional[int]
    col: Optional[int]
    code_snippet: str         # The actual line of code
    description: str          # Human-readable explanation
    suggestion: str           # What to look at (NOT the fix)


@dataclass
class FunctionProfile:
    """Deep profile of a single function"""
    name: str
    start_line: int
    param_names: List[str]
    local_variables: List[str]
    calls_itself: bool           # Recursion
    calls: List[str]             # Other functions it calls
    has_return: bool
    return_lines: List[int]
    loop_count: int
    has_base_case: bool          # Recursion base case detected
    docstring: Optional[str]


@dataclass
class CodeAnalysisResult:
    """Full AST analysis result"""
    is_valid: bool
    issues: List[CodeIssue]
    issue_locations: List[IssueLocation]   # ← NEW: issues with line numbers
    syntax_errors: List[str]
    function_count: int
    loop_count: int
    variable_count: int
    has_recursion: bool
    complexity_score: int
    code_structure: Dict[str, Any]
    # ── NEW deep analysis fields ──
    algorithm_pattern: AlgorithmPattern = AlgorithmPattern.UNKNOWN
    function_profiles: List[FunctionProfile] = field(default_factory=list)
    data_structures_used: List[str] = field(default_factory=list)  # list/dict/set/stack/queue
    concepts_detected: List[str] = field(default_factory=list)     # maps to curriculum nodes
    student_approach_summary: str = ""                              # human-readable summary
    lines: List[str] = field(default_factory=list)                  # raw code lines for context


class CodeAnalyzer:
    """Analyzes student code to understand their approach"""
    
    def __init__(self):
        self.supported_languages = ["python", "javascript"]

    # ══════════════════════════════════════════════════════
    # PRIMARY ANALYSIS  (called by tutoring engine + bridge)
    # ══════════════════════════════════════════════════════

    def analyze_python(self, code: str) -> CodeAnalysisResult:
        """
        Deep AST analysis of Python code.

        Returns a CodeAnalysisResult with:
        - Basic metrics (function count, loops, variables)
        - Issue locations with LINE NUMBERS and code snippets
        - Detected algorithm pattern (recursive / iterative / DP / etc.)
        - Function profiles (params, calls, base case, return lines)
        - Data structures in use (list / dict / set / stack / queue)
        - Curriculum concept mapping (connects to Role 3's knowledge graph)
        - Plain-English summary for LLM prompt injection
        """
        lines = code.split("\n")
        issues: List[CodeIssue] = []
        issue_locations: List[IssueLocation] = []
        syntax_errors: List[str] = []

        # ── Parse ─────────────────────────────────────────
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            loc = IssueLocation(
                issue_type=CodeIssue.SYNTAX_ERROR,
                line=e.lineno,
                col=e.offset,
                code_snippet=lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else "",
                description=f"SyntaxError: {e.msg}",
                suggestion="Check the indentation and brackets on this line."
            )
            return CodeAnalysisResult(
                is_valid=False,
                issues=[CodeIssue.SYNTAX_ERROR],
                issue_locations=[loc],
                syntax_errors=[f"Line {e.lineno}: {e.msg}"],
                function_count=0, loop_count=0, variable_count=0,
                has_recursion=False, complexity_score=0,
                code_structure={}, lines=lines
            )

        # ── Walk the AST ──────────────────────────────────
        visitor = _DeepASTVisitor(lines)
        visitor.visit(tree)

        # ── Issue detection (with locations) ──────────────
        for loop_info in visitor.while_loops:
            if not loop_info["has_break"] and not loop_info["has_return_in_loop"]:
                snippet = lines[loop_info["line"] - 1] if loop_info["line"] <= len(lines) else ""
                issues.append(CodeIssue.NO_TERMINATION)
                issue_locations.append(IssueLocation(
                    issue_type=CodeIssue.NO_TERMINATION,
                    line=loop_info["line"],
                    col=loop_info["col"],
                    code_snippet=snippet.strip(),
                    description=f"The `while` loop on line {loop_info['line']} may not terminate.",
                    suggestion=f"What condition makes `{snippet.strip()}` eventually become False?"
                ))

        for fn in visitor.function_profiles:
            if not fn.has_return and fn.calls_itself is False:
                issues.append(CodeIssue.MISSING_RETURN)
                issue_locations.append(IssueLocation(
                    issue_type=CodeIssue.MISSING_RETURN,
                    line=fn.start_line,
                    col=0,
                    code_snippet=f"def {fn.name}({', '.join(fn.param_names)}):",
                    description=f"Function `{fn.name}` has no return statement.",
                    suggestion=f"What should `{fn.name}` give back to the caller?"
                ))
            if fn.calls_itself and not fn.has_base_case:
                issues.append(CodeIssue.MISSING_BASE_CASE)
                issue_locations.append(IssueLocation(
                    issue_type=CodeIssue.MISSING_BASE_CASE,
                    line=fn.start_line,
                    col=0,
                    code_snippet=f"def {fn.name}(...):",
                    description=f"Recursive function `{fn.name}` has no detectable base case.",
                    suggestion=f"When should `{fn.name}` stop calling itself?"
                ))

        if visitor.function_count == 0 and len(code.strip()) < 10:
            issues.append(CodeIssue.EMPTY_FUNCTION)

        # ── Algorithm pattern + concepts ──────────────────
        pattern = self._detect_pattern(visitor)
        ds_used = self._detect_data_structures(visitor)
        concepts = self._map_to_concepts(visitor, pattern, ds_used)
        summary = self._build_summary(visitor, pattern, ds_used, issues)

        # ── Complexity score ──────────────────────────────
        complexity = (
            visitor.function_count * 2
            + visitor.loop_count * 3
            + visitor.conditional_count * 2
            + visitor.recursion_count * 5
            + (len(ds_used)) * 1
        )

        return CodeAnalysisResult(
            is_valid=True,
            issues=issues,
            issue_locations=issue_locations,
            syntax_errors=[],
            function_count=visitor.function_count,
            loop_count=visitor.loop_count,
            variable_count=visitor.variable_count,
            has_recursion=visitor.has_recursion,
            complexity_score=complexity,
            code_structure={
                "functions": [fp.name for fp in visitor.function_profiles],
                "loops": visitor.loops,
                "conditionals": visitor.conditional_count,
                "variables": list(visitor.variables),
            },
            algorithm_pattern=pattern,
            function_profiles=visitor.function_profiles,
            data_structures_used=ds_used,
            concepts_detected=concepts,
            student_approach_summary=summary,
            lines=lines,
        )

    # ══════════════════════════════════════════════════════
    # PATTERN DETECTION  (the "Neuro-Symbolic" part)
    # ══════════════════════════════════════════════════════

    def _detect_pattern(self, v: "_DeepASTVisitor") -> AlgorithmPattern:
        """Classify the student's algorithm approach from AST features."""
        has_recursion  = v.has_recursion
        has_memo       = any("memo" in var or "cache" in var or "dp" in var
                             for var in v.variables)
        has_2d_table   = any("table" in var or "dp" in var or "matrix" in var
                             for var in v.variables)
        nested_loops   = v.nested_loop_depth >= 2
        has_queue      = any(c in v.imported_names or c in v.variables
                             for c in ["deque", "queue", "Queue"])
        has_stack      = any("stack" in var for var in v.variables)
        has_lo_hi      = (
            ("lo" in v.variables or "left" in v.variables or "l" in v.variables) and
            ("hi" in v.variables or "right" in v.variables or "r" in v.variables)
        )

        if has_recursion and (has_memo or has_2d_table):
            return AlgorithmPattern.DYNAMIC_PROG
        if has_queue or has_stack:
            return AlgorithmPattern.BFS_DFS
        if has_recursion and has_lo_hi:
            return AlgorithmPattern.DIVIDE_CONQUER
        if has_recursion:
            return AlgorithmPattern.RECURSIVE
        if has_lo_hi and not has_recursion:
            return AlgorithmPattern.TWO_POINTER
        if nested_loops:
            return AlgorithmPattern.BRUTE_FORCE
        if v.loop_count > 0:
            return AlgorithmPattern.ITERATIVE
        return AlgorithmPattern.UNKNOWN

    def _detect_data_structures(self, v: "_DeepASTVisitor") -> List[str]:
        """Identify data structures used in the code."""
        ds: List[str] = []
        if v.uses_list:  ds.append("list")
        if v.uses_dict:  ds.append("dict")
        if v.uses_set:   ds.append("set")
        if any("stack" in var for var in v.variables): ds.append("stack")
        if any("queue" in var or "deque" in var for var in v.variables): ds.append("queue")
        if any("node" in var or "head" in var or "next" in var for var in v.variables):
            ds.append("linked_list")
        if any("tree" in var or "root" in var or "left" in var or "right" in var
               for var in v.variables if len(var) > 1):
            ds.append("tree")
        return ds

    def _map_to_concepts(
        self,
        v: "_DeepASTVisitor",
        pattern: AlgorithmPattern,
        ds_used: List[str]
    ) -> List[str]:
        """
        Map AST features → curriculum concept IDs.
        These match Role 3's Neo4j knowledge graph node names.
        """
        concepts: List[str] = []
        if pattern == AlgorithmPattern.RECURSIVE:           concepts.append("recursion")
        if pattern == AlgorithmPattern.DIVIDE_CONQUER:      concepts.extend(["recursion", "divide_and_conquer"])
        if pattern == AlgorithmPattern.DYNAMIC_PROG:        concepts.extend(["recursion", "dynamic_programming"])
        if pattern == AlgorithmPattern.TWO_POINTER:         concepts.append("two_pointers")
        if pattern == AlgorithmPattern.BFS_DFS:             concepts.extend(["graphs", "trees"])
        if pattern == AlgorithmPattern.BRUTE_FORCE:         concepts.append("time_complexity")
        if v.loop_count > 0:                                concepts.append("loops")
        if v.function_count > 0:                            concepts.append("functions")
        if v.conditional_count > 0:                         concepts.append("conditionals")
        concepts.extend(ds_used)
        return list(dict.fromkeys(concepts))  # dedup, preserve order

    def _build_summary(
        self,
        v: "_DeepASTVisitor",
        pattern: AlgorithmPattern,
        ds_used: List[str],
        issues: List[CodeIssue]
    ) -> str:
        """
        Plain-English summary injected into the LLM prompt.
        This gives the LLM the symbolic context to generate code-specific hints.
        """
        parts = []
        fnames = [fp.name for fp in v.function_profiles]
        if fnames:
            parts.append(f"defines {len(fnames)} function(s): {', '.join(fnames)}")
        parts.append(f"uses a {pattern.value.replace('_', ' ')} approach")
        if v.loop_count:
            loop_desc = ", ".join(v.loops[:3])
            parts.append(f"{v.loop_count} loop(s) ({loop_desc})")
        if ds_used:
            parts.append(f"data structures: {', '.join(ds_used)}")
        if issues:
            issue_names = [i.value.replace("_", " ") for i in issues]
            parts.append(f"potential issues: {', '.join(issue_names)}")
        if v.nested_loop_depth >= 2:
            parts.append("nested loops detected (possible O(n²) complexity)")
        return "Student's code " + "; ".join(parts) + "."

    # ══════════════════════════════════════════════════════
    # RICH CONTEXT BUILDER  (for LLM prompt injection)
    # ══════════════════════════════════════════════════════

    def build_llm_context(self, result: CodeAnalysisResult) -> dict:
        """
        Build a structured context dict for injecting into LLM prompts.
        This is what makes hints code-SPECIFIC rather than generic.
        """
        # Build function detail strings
        fn_details = []
        for fp in result.function_profiles:
            detail = f"  • `{fp.name}({', '.join(fp.param_names)})`"
            if fp.calls_itself:
                detail += " [recursive]"
            if not fp.has_base_case and fp.calls_itself:
                detail += " ⚠️ no base case"
            if not fp.has_return:
                detail += " ⚠️ no return"
            fn_details.append(detail)

        # Build issue summary strings
        issue_strings = []
        for loc in result.issue_locations:
            issue_strings.append(
                f"  • Line {loc.line}: {loc.description} → {loc.suggestion}"
            )

        return {
            "algorithm_pattern": result.algorithm_pattern.value,
            "student_approach": result.student_approach_summary,
            "functions": fn_details,
            "data_structures": result.data_structures_used,
            "concepts": result.concepts_detected,
            "issues": issue_strings,
            "complexity": result.complexity_score,
            "has_recursion": result.has_recursion,
            "loop_count": result.loop_count,
        }

    def get_code_summary(self, code: str, language: str = "python") -> str:
        """Get a human-readable one-line summary of the code"""
        if language == "python":
            result = self.analyze_python(code)
            if not result.is_valid:
                return f"Code has syntax errors: {', '.join(result.syntax_errors)}"
            return result.student_approach_summary or "Empty code"
        return "Unsupported language"


# ══════════════════════════════════════════════════════════════
# Deep AST Visitor  (replaces the original ASTAnalyzer)
# ══════════════════════════════════════════════════════════════

class _DeepASTVisitor(ast.NodeVisitor):
    """
    Walks the AST and collects deep structural information.
    Used exclusively by CodeAnalyzer; do not instantiate directly.
    """

    def __init__(self, lines: List[str]):
        self.lines = lines

        # Basic counters
        self.function_count    = 0
        self.loop_count        = 0
        self.variable_count    = 0
        self.conditional_count = 0
        self.recursion_count   = 0
        self.nested_loop_depth = 0
        self._current_loop_depth = 0

        # Flags
        self.has_return    = False
        self.has_break     = False
        self.has_recursion = False
        self.uses_list     = False
        self.uses_dict     = False
        self.uses_set      = False

        # Collections
        self.functions: List[str] = []
        self.loops: List[str] = []
        self.variables: set = set()
        self.imported_names: set = set()
        self.while_loops: List[dict] = []
        self.function_profiles: List[FunctionProfile] = []

        self._current_function: Optional[str] = None
        self._function_stack: List[str] = []

    # ── Functions ──────────────────────────────────────────
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_count += 1
        self.functions.append(node.name)

        params = [a.arg for a in node.args.args]
        local_vars: List[str] = []

        prev = self._current_function
        self._current_function = node.name
        self._function_stack.append(node.name)

        # Sub-visit to collect inner data
        sub = _FunctionBodyVisitor(node.name, self.lines)
        sub.visit(node)

        if sub.calls_itself:
            self.has_recursion = True
            self.recursion_count += sub.recursive_call_count

        profile = FunctionProfile(
            name=node.name,
            start_line=node.lineno,
            param_names=params,
            local_variables=sub.local_vars,
            calls_itself=sub.calls_itself,
            calls=sub.calls,
            has_return=sub.has_return,
            return_lines=sub.return_lines,
            loop_count=sub.loop_count,
            has_base_case=sub.has_base_case,
            docstring=ast.get_docstring(node),
        )
        self.function_profiles.append(profile)

        if sub.has_return:
            self.has_return = True

        self.generic_visit(node)
        self._function_stack.pop()
        self._current_function = prev

    visit_AsyncFunctionDef = visit_FunctionDef

    # ── Loops ──────────────────────────────────────────────
    def visit_For(self, node: ast.For):
        self.loop_count += 1
        self.loops.append(f"for (line {node.lineno})")
        self._current_loop_depth += 1
        self.nested_loop_depth = max(self.nested_loop_depth, self._current_loop_depth)
        self.generic_visit(node)
        self._current_loop_depth -= 1

    def visit_While(self, node: ast.While):
        self.loop_count += 1
        self.loops.append(f"while (line {node.lineno})")
        self._current_loop_depth += 1
        self.nested_loop_depth = max(self.nested_loop_depth, self._current_loop_depth)

        # Check if this while loop has a break or return inside it
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
        self.while_loops.append({
            "line": node.lineno,
            "col": node.col_offset,
            "has_break": has_break,
            "has_return_in_loop": has_return,
        })

        self.generic_visit(node)
        self._current_loop_depth -= 1

    # ── Control flow ───────────────────────────────────────
    def visit_If(self, node: ast.If):
        self.conditional_count += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self.has_return = True
        self.generic_visit(node)

    def visit_Break(self, node: ast.Break):
        self.has_break = True

    # ── Variables ──────────────────────────────────────────
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.variables.add(node.id)
            self.variable_count = len(self.variables)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Detect data structure literals
        if isinstance(node.value, ast.List):        self.uses_list = True
        if isinstance(node.value, ast.Dict):        self.uses_dict = True
        if isinstance(node.value, ast.Set):         self.uses_set = True
        if isinstance(node.value, ast.Call):
            fname = ""
            if isinstance(node.value.func, ast.Name):
                fname = node.value.func.id
            if fname == "list":  self.uses_list = True
            if fname == "dict":  self.uses_dict = True
            if fname == "set":   self.uses_set = True
        self.generic_visit(node)

    # ── Imports ────────────────────────────────────────────
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)


class _FunctionBodyVisitor(ast.NodeVisitor):
    """Collects details about a single function's body."""

    def __init__(self, func_name: str, lines: List[str]):
        self.func_name = func_name
        self.lines = lines
        self.local_vars: List[str] = []
        self.calls: List[str] = []
        self.calls_itself = False
        self.recursive_call_count = 0
        self.has_return = False
        self.return_lines: List[int] = []
        self.loop_count = 0
        self.has_base_case = False  # if/return at start of recursive function

    def visit_Return(self, node: ast.Return):
        self.has_return = True
        self.return_lines.append(node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.local_vars.append(node.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
            if node.func.id == self.func_name:
                self.calls_itself = True
                self.recursive_call_count += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Detect base case: if <simple_condition>: return <something>
        if self.calls_itself or True:  # check eagerly
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Return):
                self.has_base_case = True
        self.generic_visit(node)


# Keep original name as alias for backward compatibility
ASTAnalyzer = _DeepASTVisitor
