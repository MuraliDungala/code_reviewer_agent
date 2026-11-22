"""
Code Smell & Maintainability Reviewer Module
Analyzes code for structural smells, anti-patterns, and complexity across:
Python, C++, Java, JavaScript, C, and PHP.
"""

import re
from typing import List, Dict, Any


def run_smell_analysis(code: str, language: str) -> List[Dict[str, Any]]:
    """
    Analyzes code for structural code smells and maintainability issues.
    Returns a list of issue dictionaries:
    {
        "title": str,
        "type": "Code Smell",
        "severity": "HIGH" | "MEDIUM" | "LOW",
        "description": str,
        "recommendation": str
    }
    """
    smells: List[Dict[str, Any]] = []
    lines = code.split("\n")
    clean = code.strip()
    if not clean:
        return smells

    # 1. Nesting Depth Smell (> 3 levels of indentation)
    max_indent = 0
    for line in lines:
        if line.strip():
            # Count leading spaces / tabs
            leading = len(line) - len(line.lstrip())
            indent_level = leading // 4 if "    " in line else leading
            if indent_level > max_indent:
                max_indent = indent_level

    if max_indent >= 4:
        smells.append({
            "title": "Deep Nesting Smell",
            "type": "Code Smell",
            "severity": "MEDIUM",
            "description": f"Found deeply nested blocks (depth ~{max_indent}). Deeply nested loops/conditions hinder readability and increase cognitive complexity.",
            "recommendation": "Refactor using guard clauses, early returns, or decompose inner logic into dedicated helper functions."
        })

    # 2. Magic Numbers Smell
    # Look for literal numbers other than 0, 1, 2, -1, 10, 100 in arithmetic/conditions
    magic_matches = re.findall(r'(?<![a-zA-Z0-9_])([3-9]|[1-9][0-9]{2,})(?![a-zA-Z0-9_\.])', code)
    if len(magic_matches) >= 3:
        sample = ", ".join(magic_matches[:3])
        smells.append({
            "title": "Magic Numbers Smell",
            "type": "Code Smell",
            "severity": "LOW",
            "description": f"Found raw numerical literals ({sample}, ...) without descriptive named constants.",
            "recommendation": "Extract magic numbers into descriptive named constants or configuration variables."
        })

    # 3. Empty Exception / Catch Blocks (Silent Failures)
    empty_catch_patterns = [
        (r'except\s*.*?:(\s*pass|\s*\.\.\.)', "Python Empty `except: pass` Block"),
        (r'catch\s*\([^)]*\)\s*\{\s*\}', "Empty `catch` Block"),
    ]
    for pat, title in empty_catch_patterns:
        if re.search(pat, code):
            smells.append({
                "title": title,
                "type": "Code Smell",
                "severity": "HIGH",
                "description": "Catching exceptions without handling or logging silences errors and makes debugging unpredictable.",
                "recommendation": "Log the error, re-raise with context, or perform deliberate recovery action."
            })

    # 4. Long Method / File Smell
    if len(lines) > 80:
        smells.append({
            "title": "Large Code Block Smell",
            "type": "Code Smell",
            "severity": "LOW",
            "description": f"Snippet contains {len(lines)} lines. Large blocks often violate the Single Responsibility Principle.",
            "recommendation": "Break down large functions into modular, focused sub-routines."
        })

    # 5. Language Specific Smells
    if language == "Python":
        # Wildcard import
        if re.search(r'from\s+[a-zA-Z0-9_\.]+\s+import\s+\*', code):
            smells.append({
                "title": "Wildcard Import (`from ... import *`)",
                "type": "Code Smell",
                "severity": "MEDIUM",
                "description": "Wildcard imports pollute the local namespace and obscure where identifiers originate.",
                "recommendation": "Explicitly import only required functions and classes."
            })

        # Mutable default argument
        if re.search(r'def\s+[a-zA-Z_][a-zA-Z0-9_]*\([^)]*=\s*(\[\]|\{\})\)', code):
            smells.append({
                "title": "Mutable Default Parameter",
                "type": "Code Smell",
                "severity": "HIGH",
                "description": "Using mutable default arguments (e.g. `def foo(items=[])`) shares the same object across calls.",
                "recommendation": "Use `None` as the default argument and initialize inside the function body (`items = items or []`)."
            })

    elif language in ["JavaScript", "TypeScript"]:
        # var declaration
        if re.search(r'\bvar\s+[a-zA-Z_]', code):
            smells.append({
                "title": "Legacy `var` Declaration",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "`var` declarations are function-scoped and hoisted, causing subtle closure and scope bugs.",
                "recommendation": "Replace `var` with `let` (mutable) or `const` (immutable)."
            })

    elif language == "PHP":
        # Missing strict types declaration
        if "declare(strict_types=1)" not in code and "<?php" in code:
            smells.append({
                "title": "Missing Strict Types Declaration",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "PHP defaults to coercive typing unless strict mode is enabled.",
                "recommendation": "Add `declare(strict_types=1);` at the top of PHP files for type safety."
            })

    elif language in ["C", "C++"]:
        # Goto statement
        if re.search(r'\bgoto\s+[a-zA-Z_]', code):
            smells.append({
                "title": "Unstructured Control Flow (`goto`)",
                "type": "Code Smell",
                "severity": "MEDIUM",
                "description": "Use of `goto` makes control flow harder to trace and can bypass RAII or initialization.",
                "recommendation": "Refactor using structured loops, functions, or exception handling."
            })

    elif language == "SQL":
        # SELECT * code smell
        if re.search(r'(?i)SELECT\s+\*\s+FROM', code):
            smells.append({
                "title": "Wildcard Projection (`SELECT *`) Anti-Pattern",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "`SELECT *` retrieves all columns regardless of need, defeating covering indexes and inflating I/O and network transfer.",
                "recommendation": "Explicitly select only necessary column names (e.g. `SELECT id, username, email`)."
            })
        # Implicit cartesian product / old style join
        if re.search(r'(?i)FROM\s+[a-zA-Z0-9_]+\s*,\s*[a-zA-Z0-9_]+', code) and "JOIN" not in code.upper():
            smells.append({
                "title": "Implicit Comma-Separated Cartesian Join",
                "type": "Code Smell",
                "severity": "MEDIUM",
                "description": "Using comma-separated table lists in the FROM clause can accidentally generate massive Cartesian products if filters are omitted.",
                "recommendation": "Use explicit ANSI `INNER JOIN ... ON` syntax instead of comma-separated joins."
            })

    elif language == "MongoDB":
        # Deeply nested $lookup
        if code.count("$lookup") >= 2:
            smells.append({
                "title": "Multiple `$lookup` Stages in Pipeline",
                "type": "Code Smell",
                "severity": "MEDIUM",
                "description": "Chaining multiple `$lookup` operations emulates relational joins in a document database and degrades aggregation performance.",
                "recommendation": "Consider schema denormalization or embedding documents to optimize read paths."
            })
        # Missing projection in find
        if re.search(r'\.find\(\s*\{[^}]*\}\s*\)(?!\s*\.\s*(project|select))', code) and "db." in code:
            smells.append({
                "title": "Missing Field Projection in `.find()`",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "Fetching entire documents without field projection transfers redundant attributes over the wire.",
                "recommendation": "Supply a projection document e.g. `.find({ status: 'active' }, { name: 1, email: 1 })`."
            })

    elif language == "Perl":
        # Overuse of default variable $_
        if code.count("$_") >= 4:
            smells.append({
                "title": "Overuse of Topic Variable `$_`",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "Heavy reliance on implicit `$_` reduces code clarity and leads to unexpected variable clobbering in nested loops.",
                "recommendation": "Use named lexical loop variables: `foreach my $item (@items) { ... }`."
            })
        # Bareword filehandles
        if re.search(r'\b(print|close)\s+[A-Z]{3,}\b', code):
            smells.append({
                "title": "Legacy Bareword Filehandle Usage",
                "type": "Code Smell",
                "severity": "LOW",
                "description": "Bareword package-scoped filehandles (e.g. `FH`) can cause collisions across modules.",
                "recommendation": "Use lexical scalar filehandles (`open(my $fh, ...)`)."
            })

    return smells
