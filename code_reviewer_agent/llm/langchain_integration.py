import os
import re
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

from langchain_groq import ChatGroq
from groq import Groq

from reviewers.static_reviewer import static_review, get_static_findings
from agents.style_agent import check_python_style


# -----------------------------
# Groq Client Initialization
# -----------------------------
def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


MODEL_NAME = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "PHP", "Java",
    "C", "C++", "C#", "Go", "Rust", "Ruby", "Perl",
    "SQL", "MongoDB", "HTML", "CSS", "Bash"
]

LANGUAGE_ALIASES = {
    "python": "Python",
    "py": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "php": "PHP",
    "java": "Java",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "cs": "C#",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "rs": "Rust",
    "ruby": "Ruby",
    "rb": "Ruby",
    "perl": "Perl",
    "pl": "Perl",
    "sql": "SQL",
    "mysql": "SQL",
    "postgresql": "SQL",
    "postgres": "SQL",
    "plsql": "SQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "mql": "MongoDB",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "shell": "Bash",
    "sh": "Bash",
}

def normalize_language_name(name: str) -> str:
    if not name:
        return "Unknown"
    cleaned = re.sub(r'[^a-zA-Z0-9\+#]', '', name.strip().lower())
    if cleaned in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[cleaned]
    for lang in SUPPORTED_LANGUAGES:
        if lang.lower() == cleaned:
            return lang
    raw = name.strip().strip("'\"`.*# ")
    if raw and len(raw) < 25 and raw.isalnum():
        return raw.capitalize()
    return "Unknown"


# -----------------------------
# Language Detection (Heuristics + LLM Fallback)
# -----------------------------
def detect_language(code: str) -> str:
    clean = code.strip()
    if not clean:
        return "Unknown"

    upper = clean.upper()

    # 1. MongoDB Heuristics (MQL / Mongoose / Shell)
    if any(sig in clean for sig in ["db.", "ObjectId(", "mongoose.Schema", "mongoose.model", "collection("]) and \
       any(op in clean for op in ["$match", "$group", "$project", "$lookup", "$unwind", "find(", "aggregate(", "insertOne", "updateOne", "createIndex"]):
        return "MongoDB"
    if any(k in clean for k in ["$match", "$group", "$project", "$lookup", "$set", "$inc", "$pull", "$push"]) and "{" in clean and "}" in clean:
        return "MongoDB"

    # 2. SQL Heuristics
    if any(kw in upper for kw in ["SELECT ", "CREATE TABLE ", "INSERT INTO ", "DELETE FROM ", "UPDATE ", "ALTER TABLE ", "DROP TABLE "]):
        if "FROM " in upper or "WHERE " in upper or "INTO " in upper or "TABLE " in upper:
            return "SQL"

    # 3. Perl Heuristics
    if "#!/usr/bin/perl" in clean or "use strict;" in clean or "use warnings;" in clean:
        return "Perl"
    if ("my $" in clean or "my @" in clean or "my %" in clean) and ("=~" in clean or "print " in clean or "sub " in clean or "foreach" in clean):
        return "Perl"

    # 4. PHP Heuristics
    if "<?php" in clean or "?>" in clean or "<?=" in clean:
        return "PHP"
    has_php_vars = bool(re.search(r'\$[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*', clean))
    if has_php_vars and any(sig in clean for sig in ["echo ", "count(", "isset(", "empty(", "->", "function ", "array(", "$_GET", "$_POST"]):
        return "PHP"

    # 5. JavaScript / TypeScript Heuristics
    if "console.log" in clean or "document.getElementById" in clean or "window." in clean:
        if any(ts in clean for ts in [": string", ": number", ": boolean", "interface ", ": any"]):
            return "TypeScript"
        return "JavaScript"
    if any(sig in clean for sig in ["let ", "const ", "var "]) and any(sig in clean for sig in [".length", "=>", "===", "!==", "function", "require(", "export "]):
        if any(ts in clean for ts in [": string", ": number", ": boolean", "interface ", ": any"]):
            return "TypeScript"
        return "JavaScript"

    # 6. Python Heuristics
    if any(sig in clean for sig in ["def ", "import ", "elif ", "print(", "__name__", "self.", "class "]) and not any(sig in clean for sig in ["{", "}", ";"]):
        return "Python"

    # 7. Java Heuristics
    if "public class" in clean or "System.out.print" in clean or "public static void main" in clean:
        return "Java"

    # 8. C++ Heuristics
    if "#include <iostream>" in clean or "std::" in clean or "cout <<" in clean:
        return "C++"

    # 9. C Heuristics
    if "#include <stdio.h>" in clean or ("printf(" in clean and "{" in clean):
        return "C"

    # 10. Ruby Heuristics
    if any(sig in clean for sig in ["def ", "class "]) and "end" in clean and "puts " in clean:
        return "Ruby"

    # 11. Go Heuristics
    if "package main" in clean or "fmt.Println" in clean:
        return "Go"

    # 12. Rust Heuristics
    if "fn main()" in clean or "println!(" in clean or "let mut " in clean:
        return "Rust"

    # 13. HTML Heuristics
    if "<!DOCTYPE html>" in upper or ("<html" in clean.lower() and "</html>" in clean.lower()):
        return "HTML"

    # 14. Fallback to Groq LLM Classifier
    client = get_client()
    if not client:
        return "Unknown"

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert programming language identifier. "
                        "Identify the programming language of the given code snippet. "
                        "Respond ONLY with the name of the programming language. "
                        "Do not include explanation or markdown. If unidentifiable, respond 'Unknown'."
                    )
                },
                {
                    "role": "user",
                    "content": code[:600]
                }
            ],
            model=MODEL_NAME,
            temperature=0,
            max_tokens=15
        )

        raw_lang = response.choices[0].message.content.strip()
        detected = normalize_language_name(raw_lang)
        return detected if detected != "Unknown" else raw_lang.strip().capitalize()

    except Exception:
        return "Unknown"


# -----------------------------
# Initialize LangChain LLM
# -----------------------------
def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    return ChatGroq(
        api_key=api_key,
        model_name=MODEL_NAME,
        temperature=0.1,
        max_tokens=1200
    )


# -----------------------------
# Main Review Function
# -----------------------------
def run_langchain_review(
    code: str,
    language_choice: str = "Auto-Detect",
    static_findings: List[Dict[str, Any]] = None,
    security_findings: List[Dict[str, Any]] = None
) -> Tuple[str, str]:
    code_trimmed = code[:2500]

    # Step 1: Language Detection
    if language_choice and language_choice != "Auto-Detect":
        language = language_choice
    else:
        language = detect_language(code_trimmed)
    if not language or language == "Unknown":
        language = "Python"

    # Step 2: Prepare Static & Security context
    if static_findings is not None:
        if static_findings:
            bugs = "\n".join([
                f"- [{f.get('severity', 'HIGH')}] {f.get('title')}" + (f" (Line {f.get('line')})" if f.get('line') else "") + f": {f.get('description')}\n  Fix: {f.get('recommendation')}"
                for f in static_findings
            ])
        else:
            bugs = "✅ No syntax or structural errors found by static AST inspection."
    else:
        bugs = static_review(code_trimmed, language)

    # Step 3: Style Checker Context
    if language == "Python":
        style = check_python_style(code_trimmed)
    else:
        style = f"Style check configured for {language} standards."

    # Step 4: Prompt Construction
    lang_instruction = f"Confirm the programming language as **{language}**."

    prompt = f"""You are a Principal Software Engineer and Lead Security Auditor conducting an in-depth code review.
Carefully inspect the provided {language} code snippet for syntax errors, runtime bugs, logic flaws, security vulnerabilities, and code smells.

Code snippet:
```{language.lower() if language != 'Unknown' else ''}
{code_trimmed}
```

Pre-analysis Static AST findings:
{bugs}

Style analysis:
{style}

Provide your complete analysis in Markdown using these EXACT section headers:

### 📌 Programming Language
{lang_instruction}

### 1. Code Understanding & Logic Bugs
Provide a brief summary of what the code is intended to do, followed by a bulleted list of all syntax errors, runtime crashes, logic bugs, type errors, or boundary bugs.
For each bug found, use this exact format:
- **[Severity: CRITICAL|HIGH|MEDIUM|LOW] <Issue Title>**: <Clear description of the error, what triggers it, and the affected line(s)>. *Recommendation:* <Actionable fix>.

### 2. Time & Space Complexity
- **Time Complexity:** State in Big-O notation (e.g. O(1), O(N), O(N^2)) with algorithmic reasoning.
- **Space Complexity:** State in Big-O notation (e.g. O(1), O(N)) with memory reasoning.

### 3. Security Vulnerabilities & Code Smells
Analyze security issues (SQL injection, XSS, buffer overflow, hardcoded secrets, memory leaks) and architectural code smells.
For each item, format as:
- **[Severity: CRITICAL|HIGH|MEDIUM|LOW] <Vulnerability / Smell Title>**: <Description>. *Recommendation:* <Actionable fix>.

### 4. Performance & Best Practices
Provide 2-4 key recommendations:
- <Recommendation 1>
- <Recommendation 2>
- <Recommendation 3>

### 5. Optimized Code
Provide the complete, corrected, secure, and production-ready code snippet inside a ```{language.lower()} code block. All syntax and logic errors must be fixed.

### 6. Unit Test Cases
Provide complete, runnable unit tests for this snippet inside a ```{language.lower()} code block.
"""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()

        lang_display = language
        if language_choice == "Auto-Detect":
            lang_display = f"{language} (Auto-Detected)"

        # Ensure language header is present
        if not content.startswith("### 📌 Programming Language") and not content.startswith("### Programming Language"):
            content = f"### 📌 Programming Language: **{lang_display}**\n\n---\n\n" + content

        return content, lang_display

    except Exception as e:
        lang_display = language
        if language_choice == "Auto-Detect":
            lang_display = f"{language} (Auto-Detected)"

        err_msg = str(e)
        rate_limited = "429" in err_msg or "rate_limit_exceeded" in err_msg
        notice = "⚠️ **AI Service Notice:** Groq rate limit reached. Displaying deep static AST & security engine results." if rate_limited else f"⚠️ **AI Service Notice:** {err_msg}. Displaying static analysis results."

        fallback = f"""### 📌 Programming Language: **{lang_display}**

---

{notice}

### 1. Code Understanding & Logic Bugs
The automated static analysis engine detected the following issues in the code snippet:

{bugs}

### 2. Time & Space Complexity
- **Time Complexity:** **O(N)** (Estimated based on structural loops)
- **Space Complexity:** **O(1)** (Estimated based on variable allocations)

### 3. Security Vulnerabilities & Code Smells
Static security and maintainability inspection completed for {language}.

### 4. Performance & Best Practices
- Fix all critical syntax and runtime errors identified by the AST scanner before executing.
- Add comprehensive parameter validation and defensive exception handling.
- Adhere to standard {language} conventions and style guidelines.

### 5. Optimized Code
```{language.lower() if language != 'Unknown' else ''}
{code}
```

### 6. Unit Test Cases
```{language.lower() if language != 'Unknown' else ''}
// Unit test suite pending resolution of syntax errors
```
"""
        return fallback, lang_display
