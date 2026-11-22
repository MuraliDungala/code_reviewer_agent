import subprocess
import tempfile
import os
import sys
import re
from typing import List, Dict, Any


def check_python_style(code: str) -> str:
    """Runs flake8 on Python code snippets."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        tmp.write(code.encode())
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "flake8", tmp_path],
            capture_output=True,
            text=True
        )

        return result.stdout if result.stdout else "✅ No style issues found!"

    except Exception as e:
        return f"Style check skipped: {e}"

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def format_python_code(code: str) -> str:
    """Formats Python code with black."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        tmp.write(code.encode())
        tmp_path = tmp.name

    try:
        subprocess.run([sys.executable, "-m", "black", tmp_path], capture_output=True)

        with open(tmp_path, "r") as f:
            formatted = f.read()

        return formatted

    except Exception:
        return code

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def check_code_style(code: str, language: str) -> List[Dict[str, Any]]:
    """
    Performs style and lint checking across Python, JavaScript, PHP, Java, C, and C++.
    Returns a list of style violation objects:
    [
        {"rule": str, "description": str, "severity": "LOW" | "MEDIUM"}
    ]
    """
    violations = []
    lines = code.split("\n")

    # 1. Line Length Check (> 100 chars)
    long_lines = [idx + 1 for idx, l in enumerate(lines) if len(l) > 100]
    if long_lines:
        violations.append({
            "rule": "Line Length Exceeded (>100 characters)",
            "description": f"Lines {long_lines[:3]} exceed standard line length recommendation of 100 characters.",
            "severity": "LOW"
        })

    # 2. Mixed Tab and Space Indentation
    has_tabs = any("\t" in l for l in lines)
    has_spaces = any(l.startswith("    ") for l in lines)
    if has_tabs and has_spaces:
        violations.append({
            "rule": "Inconsistent Indentation",
            "description": "Detected a mixture of tabs and spaces for indentation.",
            "severity": "LOW"
        })

    # 3. Language-Specific Style Rules
    if language == "Python":
        py_flake = check_python_style(code)
        if py_flake and "✅" not in py_flake and "skipped" not in py_flake:
            for item in py_flake.strip().split("\n")[:5]:
                # Skip fatal syntax/indentation errors from style violations (handled by static AST)
                if any(err in item for err in ["SyntaxError", "E999", "E901", "E902", "IndentationError", "TabError"]):
                    continue
                # strip tmp file path from error line
                clean_item = re.sub(r'^.*?\.py:\d+:\d+:\s*', '', item)
                if clean_item.strip():
                    violations.append({
                        "rule": "PEP8 Style Violation",
                        "description": clean_item.strip(),
                        "severity": "LOW"
                    })

    elif language in ["JavaScript", "TypeScript"]:
        # Semicolon consistency
        missing_semi = [idx + 1 for idx, l in enumerate(lines) if re.search(r'(let|const|var)\s+.*?=\s*[^;{]+$', l.strip())]
        if missing_semi:
            violations.append({
                "rule": "Missing Semicolon",
                "description": f"Statements on lines {missing_semi[:3]} omit terminating semicolons (ASI hazard).",
                "severity": "LOW"
            })
        # CamelCase naming check
        if re.search(r'function\s+[a-z]+_[a-z]+', code):
            violations.append({
                "rule": "Naming Convention (CamelCase)",
                "description": "JavaScript standard recommends camelCase for function names rather than snake_case.",
                "severity": "LOW"
            })

    elif language == "PHP":
        # Missing opening PHP tag
        if "<?php" not in code and "<?" not in code:
            violations.append({
                "rule": "Missing PHP Opening Tag",
                "description": "PHP scripts should begin with `<?php`.",
                "severity": "MEDIUM"
            })
        # PSR-12 indentation check
        if any(l.startswith("\t") for l in lines):
            violations.append({
                "rule": "PSR-12 Indentation Guideline",
                "description": "PSR-12 coding standard mandates using 4 spaces instead of tabs for indentation.",
                "severity": "LOW"
            })

    elif language in ["C", "C++"]:
        # Unbounded array or C-style cast
        if re.search(r'\([a-zA-Z0-9_]+\s*\*?\)\s*[a-zA-Z0-9_]+', code) and language == "C++":
            violations.append({
                "rule": "C-Style Cast in C++",
                "description": "Found C-style cast. Prefer C++ named casts: `static_cast`, `dynamic_cast`, or `reinterpret_cast`.",
                "severity": "LOW"
            })

    elif language == "Java":
        # PascalCase Class naming
        if re.search(r'class\s+[a-z][a-zA-Z0-9_]*', code):
            violations.append({
                "rule": "Java Class Naming Convention",
                "description": "Java class names should begin with an uppercase letter (PascalCase).",
                "severity": "LOW"
            })

    return violations
