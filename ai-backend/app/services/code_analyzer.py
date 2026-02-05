"""Code Analysis Module - Analyzes student code using AST"""
import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class CodeIssue(Enum):
    """Types of issues detected in code"""
    SYNTAX_ERROR = "syntax_error"
    INFINITE_LOOP = "infinite_loop"
    MISSING_RETURN = "missing_return"
    UNUSED_VARIABLE = "unused_variable"
    NO_TERMINATION = "no_termination"
    EMPTY_FUNCTION = "empty_function"


@dataclass
class CodeAnalysisResult:
    """Result of code analysis"""
    is_valid: bool
    issues: List[CodeIssue]
    syntax_errors: List[str]
    function_count: int
    loop_count: int
    variable_count: int
    has_recursion: bool
    complexity_score: int
    code_structure: Dict[str, Any]


class CodeAnalyzer:
    """Analyzes student code to understand their approach"""
    
    def __init__(self):
        self.supported_languages = ["python", "javascript"]
    
    def analyze_python(self, code: str) -> CodeAnalysisResult:
        """
        Analyze Python code using AST
        
        Args:
            code: Python source code string
            
        Returns:
            CodeAnalysisResult with detected issues and metrics
        """
        issues = []
        syntax_errors = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return CodeAnalysisResult(
                is_valid=False,
                issues=[CodeIssue.SYNTAX_ERROR],
                syntax_errors=[f"Line {e.lineno}: {e.msg}"],
                function_count=0,
                loop_count=0,
                variable_count=0,
                has_recursion=False,
                complexity_score=0,
                code_structure={}
            )
        
        # Analyze AST
        analyzer = ASTAnalyzer()
        analyzer.visit(tree)
        
        # Check for common issues
        if analyzer.loop_count > 0 and not analyzer.has_break:
            issues.append(CodeIssue.NO_TERMINATION)
        
        if analyzer.function_count > 0 and not analyzer.has_return:
            issues.append(CodeIssue.MISSING_RETURN)
        
        if analyzer.function_count == 0 and len(code.strip()) < 10:
            issues.append(CodeIssue.EMPTY_FUNCTION)
        
        # Calculate complexity
        complexity = (
            analyzer.function_count * 2 +
            analyzer.loop_count * 3 +
            analyzer.conditional_count * 2 +
            analyzer.recursion_count * 5
        )
        
        return CodeAnalysisResult(
            is_valid=True,
            issues=issues,
            syntax_errors=[],
            function_count=analyzer.function_count,
            loop_count=analyzer.loop_count,
            variable_count=analyzer.variable_count,
            has_recursion=analyzer.has_recursion,
            complexity_score=complexity,
            code_structure={
                "functions": analyzer.functions,
                "loops": analyzer.loops,
                "conditionals": analyzer.conditional_count,
                "variables": list(analyzer.variables)
            }
        )
    
    def get_code_summary(self, code: str, language: str = "python") -> str:
        """
        Get a human-readable summary of the code
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Summary string
        """
        if language == "python":
            result = self.analyze_python(code)
            
            if not result.is_valid:
                return f"Code has syntax errors: {', '.join(result.syntax_errors)}"
            
            summary_parts = []
            
            if result.function_count > 0:
                summary_parts.append(f"{result.function_count} function(s)")
            
            if result.loop_count > 0:
                summary_parts.append(f"{result.loop_count} loop(s)")
            
            if result.has_recursion:
                summary_parts.append("uses recursion")
            
            if result.issues:
                issue_names = [issue.value.replace("_", " ") for issue in result.issues]
                summary_parts.append(f"potential issues: {', '.join(issue_names)}")
            
            return "Code contains: " + ", ".join(summary_parts) if summary_parts else "Empty code"
        
        return "Unsupported language"


class ASTAnalyzer(ast.NodeVisitor):
    """Visitor pattern to analyze Python AST"""
    
    def __init__(self):
        self.function_count = 0
        self.loop_count = 0
        self.variable_count = 0
        self.conditional_count = 0
        self.recursion_count = 0
        self.has_return = False
        self.has_break = False
        self.has_recursion = False
        self.functions = []
        self.loops = []
        self.variables = set()
        self.current_function = None
    
    def visit_FunctionDef(self, node):
        """Visit function definition"""
        self.function_count += 1
        self.functions.append(node.name)
        
        # Check for recursion
        prev_function = self.current_function
        self.current_function = node.name
        
        # Visit function body
        self.generic_visit(node)
        
        self.current_function = prev_function
    
    def visit_For(self, node):
        """Visit for loop"""
        self.loop_count += 1
        self.loops.append("for")
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Visit while loop"""
        self.loop_count += 1
        self.loops.append("while")
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Visit if statement"""
        self.conditional_count += 1
        self.generic_visit(node)
    
    def visit_Return(self, node):
        """Visit return statement"""
        self.has_return = True
        self.generic_visit(node)
    
    def visit_Break(self, node):
        """Visit break statement"""
        self.has_break = True
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """Visit variable name"""
        if isinstance(node.ctx, ast.Store):
            self.variables.add(node.id)
            self.variable_count = len(self.variables)
        
        # Check for recursion (calling current function)
        if isinstance(node.ctx, ast.Load) and node.id == self.current_function:
            self.has_recursion = True
            self.recursion_count += 1
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Visit function call"""
        # Check if calling the current function (recursion)
        if isinstance(node.func, ast.Name):
            if node.func.id == self.current_function:
                self.has_recursion = True
                self.recursion_count += 1
        
        self.generic_visit(node)
