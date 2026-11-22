"""
Static Code Reviewer Module
Provides AST-based and structural static syntax, bug, and pattern detection across:
Python, JavaScript, TypeScript, Java, C, C++, PHP, SQL, MongoDB, and Perl.
"""

import ast
import builtins
import re
from typing import List, Dict, Any, Set, Tuple


# -------------------------------------------------------------
# Bracket & Delimiter Checker (Cross-Language)
# -------------------------------------------------------------
def _check_balanced_delimiters(code: str, language: str) -> List[Dict[str, Any]]:
    findings = []
    stack = []
    matching = {')': '(', '}': '{', ']': '['}
    names = {'(': 'parenthesis', '{': 'curly brace', '[': 'square bracket'}

    # Skip delimiter checks on strings / comments
    lines = code.split("\n")
    in_block_comment = False

    for line_idx, line in enumerate(lines, 1):
        in_single_quote = False
        in_double_quote = False
        in_backtick = False
        prev_char = ''

        for col_idx, ch in enumerate(line, 1):
            # Block comment toggles
            if not in_single_quote and not in_double_quote and not in_backtick:
                if language in ["C", "C++", "Java", "JavaScript", "TypeScript", "PHP"] and prev_char == '/' and ch == '*':
                    in_block_comment = True
                    prev_char = ch
                    continue
                if in_block_comment:
                    if prev_char == '*' and ch == '/':
                        in_block_comment = False
                    prev_char = ch
                    continue

                # Single line comments
                if (language in ["C", "C++", "Java", "JavaScript", "TypeScript", "PHP"] and prev_char == '/' and ch == '/') or \
                   (language in ["Python", "Perl", "Bash"] and ch == '#') or \
                   (language == "SQL" and prev_char == '-' and ch == '-'):
                    break

            # Quote toggles (ignoring escaped quotes)
            if ch == "'" and not in_double_quote and not in_backtick and prev_char != '\\':
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote and not in_backtick and prev_char != '\\':
                in_double_quote = not in_double_quote
            elif ch == '`' and not in_single_quote and not in_double_quote and prev_char != '\\':
                in_backtick = not in_backtick

            if not in_single_quote and not in_double_quote and not in_backtick and not in_block_comment:
                if ch in "({[":
                    stack.append((ch, line_idx, col_idx))
                elif ch in ")}]":
                    expected_open = matching[ch]
                    if not stack:
                        findings.append({
                            "title": f"Unmatched Closing {names.get(expected_open, 'Delimiter').capitalize()}: '{ch}'",
                            "severity": "CRITICAL",
                            "description": f"Found unmatched closing '{ch}' on Line {line_idx}, Column {col_idx} with no prior opening delimiter.",
                            "recommendation": f"Remove extra closing '{ch}' or add the matching opening '{expected_open}'.",
                            "line": line_idx,
                            "column": col_idx,
                            "code_snippet": line.strip()
                        })
                    else:
                        top_open, top_line, top_col = stack.pop()
                        if top_open != expected_open:
                            findings.append({
                                "title": f"Mismatched Delimiters: '{top_open}' closed with '{ch}'",
                                "severity": "CRITICAL",
                                "description": f"Mismatched delimiter on Line {line_idx}, Column {col_idx}: '{top_open}' opened on Line {top_line} was closed with '{ch}'.",
                                "recommendation": f"Replace '{ch}' with the correct matching delimiter '{matching[top_open]}'.",
                                "line": line_idx,
                                "column": col_idx,
                                "code_snippet": line.strip()
                            })

            prev_char = ch

    # Any remaining unclosed delimiters
    for unclosed_ch, unclosed_line, unclosed_col in stack:
        closer = {v: k for k, v in matching.items()}[unclosed_ch]
        snippet = lines[unclosed_line - 1].strip() if unclosed_line <= len(lines) else ""
        findings.append({
            "title": f"Unclosed {names.get(unclosed_ch, 'Delimiter').capitalize()}: '{unclosed_ch}'",
            "severity": "CRITICAL",
            "description": f"Opening '{unclosed_ch}' on Line {unclosed_line}, Column {unclosed_col} is never closed.",
            "recommendation": f"Add the matching closing delimiter '{closer}' before block termination.",
            "line": unclosed_line,
            "column": unclosed_col,
            "code_snippet": snippet
        })

    return findings


# -------------------------------------------------------------
# Python AST Static Analysis Engine
# -------------------------------------------------------------
class PythonScopeAnalyzer(ast.NodeVisitor):
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.findings: List[Dict[str, Any]] = []

        base_builtins = set(dir(builtins))
        base_builtins.update([
            "__name__", "__file__", "__doc__", "__package__", "__loader__", "__spec__",
            "__annotations__", "__builtins__", "self", "cls", "args", "kwargs"
        ])
        self.scopes = [base_builtins.copy()]
        self.zero_vars: Set[str] = set()

    def current_scope(self) -> Set[str]:
        return self.scopes[-1]

    def is_defined(self, name: str) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False

    def define(self, name: str):
        self.current_scope().add(name)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.define(alias.asname or alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            if alias.name != "*":
                self.define(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.define(node.name)
        func_scope = set()
        for arg in node.args.args:
            func_scope.add(arg.arg)
        for arg in getattr(node.args, 'posonlyargs', []):
            func_scope.add(arg.arg)
        for arg in getattr(node.args, 'kwonlyargs', []):
            func_scope.add(arg.arg)
        if node.args.vararg:
            func_scope.add(node.args.vararg.arg)
        if node.args.kwarg:
            func_scope.add(node.args.kwarg.arg)

        # Check mutable default arguments
        for d in node.args.defaults + [kd for kd in node.args.kw_defaults if kd]:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                container_type = type(d).__name__.lower()
                snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                self.findings.append({
                    "title": "Mutable Default Argument in Function Definition",
                    "severity": "HIGH",
                    "description": f"Function `{node.name}` on Line {node.lineno} uses a mutable default argument ({container_type}). State will leak across function invocations.",
                    "recommendation": "Use `None` as the default argument value and initialize the container inside the function body (`if arg is None: arg = []`).",
                    "line": node.lineno,
                    "code_snippet": snippet
                })

        # Check unreachable code in function body
        self._check_unreachable_code(node.body)

        self.scopes.append(func_scope)
        for item in node.body:
            self.visit(item)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _check_unreachable_code(self, statements: List[ast.stmt]):
        terminated = False
        term_line = None
        term_type = None

        for stmt in statements:
            if terminated:
                snippet = self.lines[stmt.lineno - 1].strip() if stmt.lineno <= len(self.lines) else ""
                self.findings.append({
                    "title": "Unreachable Code Detected",
                    "severity": "MEDIUM",
                    "description": f"Statement on Line {stmt.lineno} follows a `{term_type}` on Line {term_line} and will never be executed.",
                    "recommendation": "Remove unreachable code or adjust branching logic.",
                    "line": stmt.lineno,
                    "code_snippet": snippet
                })
                break

            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True
                term_line = stmt.lineno
                term_type = type(stmt).__name__.lower()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.define(node.name)
        self.scopes.append(set())
        for item in node.body:
            self.visit(item)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign):
        self.visit(node.value)
        for target in node.targets:
            self._record_assignment(target, node.value)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.visit(node.value)
        self._record_assignment(node.target)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.value:
            self.visit(node.value)
        self._record_assignment(node.target, node.value)

    def _record_assignment(self, target: ast.AST, value_node: ast.AST = None):
        if isinstance(target, ast.Name):
            self.define(target.id)
            if value_node and isinstance(value_node, ast.Constant) and value_node.value == 0:
                self.zero_vars.add(target.id)
            elif target.id in self.zero_vars and value_node and not (isinstance(value_node, ast.Constant) and value_node.value == 0):
                self.zero_vars.discard(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._record_assignment(elt)

    def visit_For(self, node: ast.For):
        self._record_assignment(node.target)
        self.visit(node.iter)
        for item in node.body:
            self.visit(item)
        for item in node.orelse:
            self.visit(item)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While):
        # Check infinite loop: while True without break/return
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_exit = any(
                isinstance(n, (ast.Break, ast.Return, ast.Raise))
                for n in ast.walk(node)
            )
            if not has_exit:
                snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                self.findings.append({
                    "title": "Infinite Loop (`while True:` without exit)",
                    "severity": "CRITICAL",
                    "description": f"Loop on Line {node.lineno} runs infinitely without a `break`, `return`, or exit statement.",
                    "recommendation": "Add a termination check or break condition inside the loop body.",
                    "line": node.lineno,
                    "code_snippet": snippet
                })
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._record_assignment(item.optional_vars)
        for item in node.body:
            self.visit(item)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.name:
            self.define(node.name)
        snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
        if node.type is None:
            self.findings.append({
                "title": "Bare `except:` Clause",
                "severity": "MEDIUM",
                "description": f"Bare `except:` on Line {node.lineno} intercepts critical system exits (KeyboardInterrupt, SystemExit).",
                "recommendation": "Specify exception class explicitly: `except Exception:` or specific error types.",
                "line": node.lineno,
                "code_snippet": snippet
            })
        elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append({
                "title": "Silent Exception Swallowing (`except: pass`)",
                "severity": "HIGH",
                "description": f"Empty exception handler on Line {node.lineno} silences errors without logging or remediation.",
                "recommendation": "Log the exception or handle the failure appropriately.",
                "line": node.lineno,
                "code_snippet": snippet
            })
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        self.scopes.append(set())
        for gen in node.generators:
            self._record_assignment(gen.target)
            self.visit(gen.iter)
            for if_expr in gen.ifs:
                self.visit(if_expr)
        self.visit(node.elt)
        self.scopes.pop()

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node: ast.DictComp):
        self.scopes.append(set())
        for gen in node.generators:
            self._record_assignment(gen.target)
            self.visit(gen.iter)
            for if_expr in gen.ifs:
                self.visit(if_expr)
        self.visit(node.key)
        self.visit(node.value)
        self.scopes.pop()

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.findings.append({
                    "title": "Division by Zero (ZeroDivisionError)",
                    "severity": "CRITICAL",
                    "description": f"Explicit division or modulo by literal `0` on Line {node.lineno}.",
                    "recommendation": "Check and ensure divisor is non-zero before division.",
                    "line": node.lineno,
                    "code_snippet": snippet
                })
            elif isinstance(node.right, ast.Name) and node.right.id in self.zero_vars:
                self.findings.append({
                    "title": "ZeroDivisionError: Divisor Evaluates to 0",
                    "severity": "CRITICAL",
                    "description": f"Variable `{node.right.id}` on Line {node.lineno} was initialized to `0` and used as a divisor.",
                    "recommendation": "Ensure divisor variable cannot be 0, or validate with a condition before division.",
                    "line": node.lineno,
                    "code_snippet": snippet
                })
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(comparator, ast.Constant):
                if comparator.value is not None:
                    snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                    self.findings.append({
                        "title": "Comparison Using 'is' with Literal",
                        "severity": "MEDIUM",
                        "description": f"Using `is` with literal `{repr(comparator.value)}` on Line {node.lineno} tests identity rather than equality.",
                        "recommendation": f"Use `==` or `!=` instead of `is` / `is not` for literal comparisons.",
                        "line": node.lineno,
                        "code_snippet": snippet
                    })
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            if not self.is_defined(node.id):
                snippet = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                self.findings.append({
                    "title": f"Undefined Variable / NameError: '{node.id}'",
                    "severity": "CRITICAL",
                    "description": f"Identifier `{node.id}` on Line {node.lineno} is accessed before definition or import.",
                    "recommendation": f"Define, initialize, or import `{node.id}` before referencing it.",
                    "line": node.lineno,
                    "code_snippet": snippet
                })
        self.generic_visit(node)


def _analyze_python_code(code: str) -> List[Dict[str, Any]]:
    findings = []
    lines = code.split("\n")

    # Step 1: AST Parsing Check (Fatal Syntax/Indentation Errors)
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        err_line = e.lineno or 1
        err_col = e.offset or 1
        snippet = (lines[err_line - 1] if 0 < err_line <= len(lines) else "").strip()
        msg = e.msg or "Invalid syntax"

        rec = "Check Python syntax and correct the highlighted line."
        if "expected ':'" in msg or "expected ':'" in str(e):
            rec = "Add a missing colon (`:`) at the end of the statement header (e.g. def, if, for, while, class)."
        elif "unexpected indent" in msg:
            rec = "Align this line's indentation with the current code block level."
        elif "expected an indented block" in msg:
            rec = "Provide an indented block beneath this header, or add `pass` if temporarily empty."
        elif "unterminated string" in msg or "EOL while scanning" in msg:
            rec = "Ensure string literals are properly closed with matching quotes (' or \")."
        elif "unmatched" in msg:
            rec = "Ensure all brackets, parentheses, and braces are correctly matched and closed."

        findings.append({
            "title": f"{e.__class__.__name__}: {msg.capitalize()}",
            "severity": "CRITICAL",
            "description": f"Syntax error on Line {err_line}, Column {err_col}: `{snippet}`. Detail: {msg}",
            "recommendation": rec,
            "line": err_line,
            "column": err_col,
            "code_snippet": snippet
        })
        return findings

    # Step 2: Semantic Scope & AST Pattern Analysis
    analyzer = PythonScopeAnalyzer(lines)
    analyzer.visit(tree)
    findings.extend(analyzer.findings)

    # Heuristic checks
    clean = code.strip()
    if "def " not in clean and "class " not in clean and len(lines) > 5:
        findings.append({
            "title": "Missing Functional/Modular Structure",
            "severity": "LOW",
            "description": "No functions or classes detected. Modular code is easier to maintain and test.",
            "recommendation": "Wrap logic in dedicated functions or a class."
        })

    return findings


# -------------------------------------------------------------
# JavaScript & TypeScript Static Analysis
# -------------------------------------------------------------
def _analyze_javascript_code(code: str, language: str) -> List[Dict[str, Any]]:
    findings = []
    lines = code.split("\n")

    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()

        # Typo checks on standard globals
        if re.search(r'\b(consol|cosnole|conosle)\.log\b', clean_line):
            findings.append({
                "title": "ReferenceError: Typo in 'console.log'",
                "severity": "CRITICAL",
                "description": f"Typo in console reference on Line {idx}: `{clean_line}`.",
                "recommendation": "Correct spelling to `console.log`.",
                "line": idx,
                "code_snippet": clean_line
            })

        if re.search(r'\b(documnet|docuemnt)\.', clean_line):
            findings.append({
                "title": "ReferenceError: Typo in 'document'",
                "severity": "CRITICAL",
                "description": f"Typo in document object on Line {idx}: `{clean_line}`.",
                "recommendation": "Correct spelling to `document`.",
                "line": idx,
                "code_snippet": clean_line
            })

        # Division by zero
        if re.search(r'/\s*0(?![0-9\.])', clean_line):
            findings.append({
                "title": "Division by Zero Bug",
                "severity": "CRITICAL",
                "description": f"Explicit division by zero (`/ 0`) on Line {idx}.",
                "recommendation": "Check that the divisor is non-zero before division.",
                "line": idx,
                "code_snippet": clean_line
            })

        # Loose equality
        if re.search(r'[^\!=]==[^=]', clean_line):
            findings.append({
                "title": "Loose Equality Comparison (`==`)",
                "severity": "MEDIUM",
                "description": f"Loose equality `==` on Line {idx} performs implicit type coercion.",
                "recommendation": "Use strict equality `===` or `!==`.",
                "line": idx,
                "code_snippet": clean_line
            })

        # Assignment in conditional check
        if re.search(r'\bif\s*\(\s*[a-zA-Z0-9_\$]+\s*=[^=]', clean_line):
            findings.append({
                "title": "Assignment Inside Condition",
                "severity": "HIGH",
                "description": f"Detected assignment (`=`) instead of comparison (`===`) in `if` condition on Line {idx}.",
                "recommendation": "Use comparison operator `===` instead of assignment `=`.",
                "line": idx,
                "code_snippet": clean_line
            })

    return findings


# -------------------------------------------------------------
# PHP Static Analysis
# -------------------------------------------------------------
def _analyze_php_code(code: str) -> List[Dict[str, Any]]:
    findings = []
    lines = code.split("\n")
    clean = code.strip()

    if "<?php" not in clean and "<?" not in clean:
        findings.append({
            "title": "Missing PHP Opening Tag",
            "severity": "MEDIUM",
            "description": "PHP code must start with `<?php` to be interpreted by the PHP engine.",
            "recommendation": "Add `<?php` at the beginning of the file."
        })

    # Find uninitialized variable in accumulation loops (e.g. $total += ...)
    initialized_vars = set()
    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()

        # Assignments
        assign_match = re.match(r'\$([a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*)\s*=', clean_line)
        if assign_match and not clean_line.startswith(("$total +=", "$sum +=")):
            initialized_vars.add(assign_match.group(1))

        # Check accumulation without init
        acc_match = re.search(r'\$([a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*)\s*\+=', clean_line)
        if acc_match:
            var_name = acc_match.group(1)
            if var_name not in initialized_vars:
                findings.append({
                    "title": f"Undefined Variable (`${var_name}` in accumulation)",
                    "severity": "HIGH",
                    "description": f"Variable `${var_name}` on Line {idx} is accumulated (`+=`) before initialization.",
                    "recommendation": f"Initialize `${var_name} = 0;` before the loop.",
                    "line": idx,
                    "code_snippet": clean_line
                })
                initialized_vars.add(var_name)

        # Division by zero
        if re.search(r'/\s*0(?![0-9\.])', clean_line):
            findings.append({
                "title": "Division by Zero (DivisionByZeroError)",
                "severity": "CRITICAL",
                "description": f"Explicit division by zero (`/ 0`) on Line {idx}.",
                "recommendation": "Validate that the divisor is non-zero before division.",
                "line": idx,
                "code_snippet": clean_line
            })

    return findings


# -------------------------------------------------------------
# C & C++ Static Analysis
# -------------------------------------------------------------
def _analyze_c_cpp_code(code: str, language: str) -> List[Dict[str, Any]]:
    findings = []
    lines = code.split("\n")

    unsafe_funcs = [
        ("gets", "CRITICAL", "The `gets()` function does not perform bounds checking and is inherently insecure."),
        ("strcpy", "HIGH", "Unbounded buffer copy with `strcpy()` can lead to stack/heap buffer overflow."),
        ("sprintf", "HIGH", "`sprintf()` without buffer limits can overflow destination buffers."),
        ("strcat", "MEDIUM", "`strcat()` can exceed buffer capacity if not strictly bounded.")
    ]

    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()

        for func, sev, desc in unsafe_funcs:
            if re.search(rf'\b{func}\s*\(', clean_line):
                findings.append({
                    "title": f"Unsafe C String Function: {func}()",
                    "severity": sev,
                    "description": f"Use of `{func}()` on Line {idx}. {desc}",
                    "recommendation": f"Replace with safe bounded alternatives (`snprintf()`, `strncpy()`, or `std::string` in C++).",
                    "line": idx,
                    "code_snippet": clean_line
                })

        if re.search(r'/\s*0(?![0-9\.])', clean_line):
            findings.append({
                "title": "Division by Zero Bug",
                "severity": "CRITICAL",
                "description": f"Explicit division by zero (`/ 0`) on Line {idx}.",
                "recommendation": "Validate divisor before executing division.",
                "line": idx,
                "code_snippet": clean_line
            })

    # Memory leak check: malloc/new vs free/delete
    alloc_count = len(re.findall(r'\b(malloc|calloc|realloc)\b', code))
    free_count = len(re.findall(r'\bfree\b', code))
    if alloc_count > free_count:
        findings.append({
            "title": "Memory Leak: Unfreed Dynamic Allocations",
            "severity": "HIGH",
            "description": f"Detected {alloc_count} dynamic allocation(s) (`malloc`/`calloc`), but only {free_count} `free()` call(s).",
            "recommendation": "Ensure every dynamically allocated pointer is released with `free()` or use RAII in C++."
        })

    return findings


# -------------------------------------------------------------
# Java Static Analysis
# -------------------------------------------------------------
def _analyze_java_code(code: str) -> List[Dict[str, Any]]:
    findings = []
    lines = code.split("\n")
    clean = code.strip()

    if "public class" not in clean and "class " not in clean:
        findings.append({
            "title": "Missing Java Class Declaration",
            "severity": "HIGH",
            "description": "Java requires code to reside within a class definition.",
            "recommendation": "Wrap methods and fields inside a public class."
        })

    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()

        # String == check
        if re.search(r'[a-zA-Z0-9_]+\s*==\s*["\']', clean_line) or re.search(r'["\']\s*==\s*[a-zA-Z0-9_]+', clean_line):
            findings.append({
                "title": "String Identity Comparison (`==`) Instead of `.equals()`",
                "severity": "HIGH",
                "description": f"String equality checked with `==` on Line {idx}. In Java, `==` compares object references, not string contents.",
                "recommendation": "Use `.equals()` or `Objects.equals(a, b)` for string comparisons.",
                "line": idx,
                "code_snippet": clean_line
            })

        if re.search(r'/\s*0(?![0-9\.])', clean_line):
            findings.append({
                "title": "ArithmeticException: Division by Zero",
                "severity": "CRITICAL",
                "description": f"Explicit division by zero on Line {idx}.",
                "recommendation": "Check divisor before executing division.",
                "line": idx,
                "code_snippet": clean_line
            })

    return findings


# -------------------------------------------------------------
# SQL Static Analysis
# -------------------------------------------------------------
def _analyze_sql_code(code: str) -> List[Dict[str, Any]]:
    findings = []
    clean_upper = code.upper()

    if "DELETE FROM" in clean_upper and "WHERE" not in clean_upper:
        findings.append({
            "title": "Unconditional DELETE Statement",
            "severity": "CRITICAL",
            "description": "DELETE statement without a WHERE clause will delete all rows from the table.",
            "recommendation": "Add a WHERE clause specifying the target records."
        })

    if "UPDATE " in clean_upper and "WHERE" not in clean_upper:
        findings.append({
            "title": "Unconditional UPDATE Statement",
            "severity": "CRITICAL",
            "description": "UPDATE statement without a WHERE clause will overwrite all records in the table.",
            "recommendation": "Specify target row criteria using WHERE."
        })

    # Cartesian join: SELECT ... FROM a, b without WHERE or JOIN
    if re.search(r'FROM\s+[a-zA-Z0-9_]+(\s+[a-zA-Z0-9_]+)?\s*,\s*[a-zA-Z0-9_]+', clean_upper) and "WHERE" not in clean_upper and "JOIN" not in clean_upper:
        findings.append({
            "title": "Cartesian Product Join Hazard",
            "severity": "HIGH",
            "description": "Cross-table comma syntax without a WHERE or ON clause produces an unbounded Cartesian join.",
            "recommendation": "Use explicit `INNER JOIN ... ON ...` syntax or define join conditions."
        })

    return findings


# -------------------------------------------------------------
# MongoDB Static Analysis
# -------------------------------------------------------------
def _analyze_mongodb_code(code: str) -> List[Dict[str, Any]]:
    findings = []

    if "$where" in code:
        findings.append({
            "title": "Unsafe $where JavaScript Clause",
            "severity": "CRITICAL",
            "description": "Found `$where` clause. It evaluates arbitrary JavaScript on the database host and opens NoSQL injection vectors.",
            "recommendation": "Use native query operators (`$eq`, `$gt`, etc.) or `$expr`."
        })

    if re.search(r'(\.deleteMany|\.updateMany)\s*\(\s*\{\s*\}\s*\)', code):
        findings.append({
            "title": "Unbounded Mutation Query (`deleteMany({})`)",
            "severity": "CRITICAL",
            "description": "Invoking `deleteMany({})` or `updateMany({})` with an empty filter modifies or removes all records in the collection.",
            "recommendation": "Specify document filter criteria to avoid unintended data loss."
        })

    return findings


# -------------------------------------------------------------
# Main Static Review Entrypoint
# -------------------------------------------------------------
def get_static_findings(code: str, language: str) -> List[Dict[str, Any]]:
    """
    Analyzes code for structural and syntax bugs statically across all supported languages.
    Returns structured list of findings with severity, title, line, snippet, and recommendation.
    """
    findings: List[Dict[str, Any]] = []
    clean = code.strip()
    if not clean:
        return findings

    # 1. Delimiter balance check (Parentheses, Brackets, Braces)
    delimiter_findings = _check_balanced_delimiters(code, language)
    findings.extend(delimiter_findings)

    # 2. Language-Specific AST & Static Analyzers
    if language == "Python":
        findings.extend(_analyze_python_code(code))

    elif language in ["JavaScript", "TypeScript"]:
        findings.extend(_analyze_javascript_code(code, language))

    elif language == "PHP":
        findings.extend(_analyze_php_code(code))

    elif language in ["C", "C++"]:
        findings.extend(_analyze_c_cpp_code(code, language))

    elif language == "Java":
        findings.extend(_analyze_java_code(code))

    elif language == "SQL":
        findings.extend(_analyze_sql_code(code))

    elif language == "MongoDB":
        findings.extend(_analyze_mongodb_code(code))

    elif language == "Perl":
        if "use strict;" not in clean:
            findings.append({
                "title": "Missing `use strict;` Pragma",
                "severity": "MEDIUM",
                "description": "Perl scripts should enable `use strict;` to enforce variable declarations and prevent accidental global scoping.",
                "recommendation": "Add `use strict;` at the top of the file."
            })

    # Global division by zero check if not already reported
    has_div_zero = any("division by zero" in f["title"].lower() or "zerodivision" in f["title"].lower() for f in findings)
    if not has_div_zero and re.search(r'/\s*0(?![0-9\.])', clean):
        findings.append({
            "title": "Division by Zero Bug",
            "severity": "CRITICAL",
            "description": "Explicit division by zero detected (`/ 0`).",
            "recommendation": "Validate divisor before executing division."
        })

    return findings


def static_review(code: str, language: str) -> str:
    """
    Backwards-compatible string renderer for static reviews.
    """
    findings = get_static_findings(code, language)
    feedback = f"### 🔍 {language} Code Review (Static Mode)\n\n"

    if not code.strip():
        return "❌ Error: No code provided for analysis."

    if not findings:
        feedback += "✅ No critical static bugs detected.\n"
    else:
        for f in findings:
            icon = "🚨" if f["severity"] == "CRITICAL" else ("⚠️" if f["severity"] == "HIGH" else "💡")
            line_str = f" [Line {f['line']}]" if f.get("line") else ""
            feedback += f"- {icon} **{f['title']}** [{f['severity']}]{line_str}: {f['description']}\n  *Fix:* {f['recommendation']}\n"

    feedback += "\n\n*Note: Static AST and heuristic checks run instantaneously.*"
    return feedback
