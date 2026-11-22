"""
Auto-Fix Generator Agent
Generates clean, secure, and idiomatic fixed code addressing all bugs,
security vulnerabilities, style violations, and code smells.
Produces unified and line-by-line diffs for before/after comparison.
"""

import os
import re
import difflib
from typing import List, Dict, Any
from groq import Groq


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


MODEL_NAME = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")


def generate_autofix(code: str, language: str, issues_summary: str = "") -> str:
    """
    Produces the corrected, optimal, and secure version of the code.
    """
    client = get_client()
    if client:
        prompt = f"""You are an expert automated refactoring and auto-fix agent.
Provide the complete, corrected, and production-ready version of the provided {language} code.

Issues to fix:
{issues_summary if issues_summary else "Fix all bugs, division-by-zero, syntax errors, security vulnerabilities, and code smells."}

Requirements:
1. Return ONLY the complete fixed code block inside standard markdown backticks (e.g. ```{language.lower()} ... ```).
2. Fix any syntax errors, division-by-zero, logic bugs, and security risks.
3. Add proper input validation and error handling.
4. Follow {language} best practices and idiomatic style.
5. Do NOT include explanatory conversational text outside the code block.

Original Code:
```{language.lower()}
{code[:2000]}
```
"""
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a Senior {language} Staff Engineer providing exact, production-ready code fixes."},
                    {"role": "user", "content": prompt}
                ],
                model=MODEL_NAME,
                temperature=0.1,
                max_tokens=900
            )
            raw = response.choices[0].message.content.strip()
            # Extract code between backticks if present
            if "```" in raw:
                parts = raw.split("```")
                if len(parts) >= 3:
                    code_block = parts[1]
                    # strip language identifier on first line if present
                    first_nl = code_block.find("\n")
                    if first_nl != -1 and not code_block[:first_nl].strip().endswith((";", "{", ":", ")")):
                        return code_block[first_nl + 1:].rstrip()
                    return code_block.rstrip()
            return raw
        except Exception:
            pass

    # Fallback: clean up trivial division by zero or formatting
    return _fallback_fix(code, language)


def _fallback_fix(code: str, language: str) -> str:
    """Lightweight deterministic fallback fixes for common syntax & logic bugs."""
    fixed = code

    # 1. Fix missing colons in Python definitions and blocks
    if language == "Python":
        fixed = re.sub(r'(?m)^(def\s+[a-zA-Z0-9_]+\([^)]*\))(?!\s*:)\s*$', r'\1:', fixed)
        fixed = re.sub(r'(?m)^(if\s+[^:]+)(?!\s*:)\s*$', r'\1:', fixed)
        fixed = re.sub(r'(?m)^(for\s+[^:]+)(?!\s*:)\s*$', r'\1:', fixed)
        fixed = re.sub(r'(?m)^(while\s+[^:]+)(?!\s*:)\s*$', r'\1:', fixed)
        fixed = re.sub(r'(?m)^(class\s+[a-zA-Z0-9_]+(\([^)]*\))?)(?!\s*:)\s*$', r'\1:', fixed)

    # 2. Fix explicit division by zero (replace literal 0 divisor with 1 or guard)
    if re.search(r'/\s*0(?![0-9\.])', fixed):
        if language == "Python":
            fixed = re.sub(r'/\s*0(?![0-9\.])', '/ 1  # Note: Divisor guarded against zero', fixed)
        elif language in ["JavaScript", "TypeScript", "Java", "C", "C++", "PHP"]:
            fixed = re.sub(r'/\s*0(?![0-9\.])', '/ 1 /* Note: Divisor guarded against zero */', fixed)
        elif language == "Perl":
            fixed = re.sub(r'/\s*0(?![0-9\.])', '/ 1 # Note: Divisor guarded against zero', fixed)

    # 3. Fix JavaScript common typos
    if language in ["JavaScript", "TypeScript"]:
        fixed = re.sub(r'\b(consol|cosnole|conosle)\.log\b', 'console.log', fixed)
        fixed = re.sub(r'\b(documnet|docuemnt)\.', 'document.', fixed)
        # Fix assignment in if-condition: if (discount = 0) -> if (discount === 0)
        fixed = re.sub(r'\bif\s*\(\s*([a-zA-Z0-9_\$]+)\s*=\s*([a-zA-Z0-9_\$"\']+)\s*\)', r'if (\1 === \2)', fixed)

    # 4. Fix missing PHP opening tag
    if language == "PHP" and "<?php" not in fixed and "<?" not in fixed:
        fixed = "<?php\n" + fixed

    # 5. Fix SQL DELETE without WHERE
    if language == "SQL" and "DELETE FROM" in fixed.upper() and "WHERE" not in fixed.upper():
        if ";" in fixed:
            fixed = fixed.replace(";", " WHERE id = :target_id; -- Added WHERE safety filter", 1)
        else:
            fixed = fixed + " WHERE id = :target_id; -- Added WHERE safety filter"

    return fixed


def compute_unified_diff(original: str, fixed: str, filename: str = "snippet") -> str:
    """Computes a standard git-style unified diff."""
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        fixed_lines,
        fromfile=f"Original ({filename})",
        tofile=f"Auto-Fixed ({filename})",
        lineterm=""
    )
    return "".join(diff)


def compute_line_diff(original: str, fixed: str) -> List[Dict[str, Any]]:
    """
    Computes a structured line-by-line diff for rich Streamlit UI rendering.
    Returns list of {'type': 'added'|'removed'|'unchanged', 'text': str, 'orig_no': int, 'new_no': int}
    """
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()

    matcher = difflib.SequenceMatcher(None, orig_lines, fixed_lines)
    result = []
    orig_idx = 1
    new_idx = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in orig_lines[i1:i2]:
                result.append({"type": "unchanged", "text": line, "orig_no": orig_idx, "new_no": new_idx})
                orig_idx += 1
                new_idx += 1
        elif tag == 'replace':
            for line in orig_lines[i1:i2]:
                result.append({"type": "removed", "text": line, "orig_no": orig_idx, "new_no": None})
                orig_idx += 1
            for line in fixed_lines[j1:j2]:
                result.append({"type": "added", "text": line, "orig_no": None, "new_no": new_idx})
                new_idx += 1
        elif tag == 'delete':
            for line in orig_lines[i1:i2]:
                result.append({"type": "removed", "text": line, "orig_no": orig_idx, "new_no": None})
                orig_idx += 1
        elif tag == 'insert':
            for line in fixed_lines[j1:j2]:
                result.append({"type": "added", "text": line, "orig_no": None, "new_no": new_idx})
                new_idx += 1

    return result
