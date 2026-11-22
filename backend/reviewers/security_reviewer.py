"""
Security Reviewer Module
Performs pattern-based and structural security vulnerability detection across:
Python, C++, Java, JavaScript, C, and PHP.
"""

import re
from typing import List, Dict, Any


def run_security_analysis(code: str, language: str) -> List[Dict[str, Any]]:
    """
    Analyzes code for security vulnerabilities.
    Returns a list of issue dictionaries:
    {
        "title": str,
        "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
        "cwe": str,
        "description": str,
        "recommendation": str,
        "line_hint": str (optional)
    }
    """
    issues: List[Dict[str, Any]] = []
    clean = code.strip()
    if not clean:
        return issues

    # -------------------------------------------------------------
    # Cross-Language Common Vulnerabilities
    # -------------------------------------------------------------
    # 1. Hardcoded Secrets / API Keys / Passwords
    secret_patterns = [
        (r'(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token)\s*=\s*["\'][a-zA-Z0-9_\-\.]{12,}["\']', "Potential Hardcoded Secret/API Key", "HIGH", "CWE-798"),
        (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded Password/Credential", "HIGH", "CWE-259"),
        (r'(?i)-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----', "Embedded Private Cryptographic Key", "CRITICAL", "CWE-321"),
    ]
    for pattern, title, sev, cwe in secret_patterns:
        match = re.search(pattern, code)
        if match:
            issues.append({
                "title": title,
                "severity": sev,
                "cwe": cwe,
                "description": f"Found pattern matching hardcoded credential or secret: `{match.group(0)[:30]}...`",
                "recommendation": "Use environment variables, secrets managers, or secure vault storage instead of committing plaintext secrets."
            })

    # 2. Division by Zero (Common to all)
    if re.search(r'/\s*0(?![0-9\.])', code):
        issues.append({
            "title": "Division by Zero",
            "severity": "CRITICAL",
            "cwe": "CWE-369",
            "description": "Code contains explicit division by zero (`/ 0`), which causes unhandled runtime exceptions or infinite values.",
            "recommendation": "Check that the divisor is non-zero before performing division."
        })

    # -------------------------------------------------------------
    # Language Specific Security Checks
    # -------------------------------------------------------------
    if language == "Python":
        # Python Insecure Deserialization
        if "pickle.loads(" in code or "pickle.load(" in code or "_pickle" in code:
            issues.append({
                "title": "Insecure Deserialization (Pickle)",
                "severity": "CRITICAL",
                "cwe": "CWE-502",
                "description": "Unpickling untrusted data can lead to arbitrary remote code execution (RCE).",
                "recommendation": "Use safer serialization formats like JSON, protocol buffers, or cryptography-signed payloads."
            })

        # Python eval / exec
        if re.search(r'\b(eval|exec)\s*\(', code):
            issues.append({
                "title": "Arbitrary Code Execution via eval/exec",
                "severity": "CRITICAL",
                "cwe": "CWE-95",
                "description": "Use of `eval()` or `exec()` allows execution of arbitrary Python code if inputs are untrusted.",
                "recommendation": "Avoid `eval()` and `exec()`. Use `ast.literal_eval()` for safely parsing literals."
            })

        # Command Injection
        if re.search(r'(os\.system|subprocess\.Popen|subprocess\.run|subprocess\.call)\s*\([^)]*shell\s*=\s*True', code) or \
           re.search(r'os\.system\s*\(', code):
            issues.append({
                "title": "Command Injection Vulnerability",
                "severity": "CRITICAL",
                "cwe": "CWE-78",
                "description": "Invoking shell commands with `shell=True` or `os.system` using dynamic strings allows command injection.",
                "recommendation": "Pass arguments as an explicit list with `shell=False` in `subprocess.run()`, avoiding shell interpolation."
            })

        # SQL Injection via string formatting or f-strings
        if re.search(r'(?i)(execute|cursor\.execute)\s*\(\s*(f["\']|["\'].*?%|.*?\.format\()', code) or \
           re.search(r'(?i)f["\'].*?(SELECT|INSERT|UPDATE|DELETE)\b', code) or \
           re.search(r'(?i)(SELECT|INSERT|UPDATE|DELETE)\s+.*?\bf["\']', code):
            issues.append({
                "title": "Potential SQL Injection",
                "severity": "HIGH",
                "cwe": "CWE-89",
                "description": "SQL query built via string formatting or dynamic f-strings instead of parameterized queries.",
                "recommendation": "Use parameterized queries: `cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))`."
            })

    elif language == "PHP":
        # PHP SQL Injection
        if re.search(r'(mysqli_query|mysql_query|pg_query)\s*\([^,]+,\s*["\'].*?\$(?:_[A-Z]+|[a-zA-Z_])', code) or \
           re.search(r'->query\s*\(\s*["\'].*?\$(?:_[A-Z]+|[a-zA-Z_])', code):
            issues.append({
                "title": "SQL Injection in PHP",
                "severity": "CRITICAL",
                "cwe": "CWE-89",
                "description": "SQL query constructed with unescaped PHP variables.",
                "recommendation": "Use PDO or MySQLi prepared statements with parameter binding."
            })

        # PHP XSS
        if re.search(r'echo\s+.*?(\$_GET|\$_POST|\$_REQUEST|\$_COOKIE|\$input|\$name|\$user)', code) and "htmlspecialchars" not in code and "htmlentities" not in code:
            issues.append({
                "title": "Cross-Site Scripting (XSS) in PHP",
                "severity": "HIGH",
                "cwe": "CWE-79",
                "description": "Outputting variables directly to the page without HTML encoding allows script injection.",
                "recommendation": "Wrap dynamic outputs with `htmlspecialchars($var, ENT_QUOTES, 'UTF-8')`."
            })

        # PHP Command Injection
        if re.search(r'\b(shell_exec|exec|system|passthru|popen)\s*\(', code):
            issues.append({
                "title": "Command Execution in PHP",
                "severity": "CRITICAL",
                "cwe": "CWE-78",
                "description": "Direct system command execution function detected.",
                "recommendation": "Sanitize inputs using `escapeshellcmd()` and `escapeshellarg()`, or avoid shell execution."
            })

        # Insecure File Inclusion
        if re.search(r'\b(include|require|include_once|require_once)\s*\(?.*?\$(?:_GET|_POST)', code):
            issues.append({
                "title": "Remote/Local File Inclusion (LFI/RFI)",
                "severity": "CRITICAL",
                "cwe": "CWE-98",
                "description": "Including files determined by user-controlled input can execute arbitrary files.",
                "recommendation": "Whitelist allowed files rather than accepting input paths directly."
            })

    elif language in ["JavaScript", "TypeScript"]:
        # XSS via innerHTML or document.write
        if re.search(r'\.(innerHTML|outerHTML)\s*=', code) or "document.write(" in code:
            issues.append({
                "title": "DOM-Based Cross-Site Scripting (XSS)",
                "severity": "HIGH",
                "cwe": "CWE-79",
                "description": "Modifying `innerHTML` or calling `document.write` with untrusted data can execute malicious scripts.",
                "recommendation": "Use `textContent`, `innerText`, or a safe DOM sanitizer like DOMPurify."
            })

        # JS eval / Function constructor
        if re.search(r'\b(eval|setTimeout|setInterval)\s*\(\s*["\']', code) or "new Function(" in code:
            issues.append({
                "title": "Unsafe Dynamic Code Execution",
                "severity": "HIGH",
                "cwe": "CWE-95",
                "description": "Evaluating code dynamically via `eval` or string-based timers introduces code injection risks.",
                "recommendation": "Pass function references directly and use `JSON.parse` for parsing structured data."
            })

        # Loose equality
        if re.search(r'[^\!=]==[^=]', code):
            issues.append({
                "title": "Loose Equality Comparison (`==`)",
                "severity": "LOW",
                "cwe": "CWE-697",
                "description": "Loose equality operator `==` performs implicit type coercion which can bypass authentication or type checks.",
                "recommendation": "Use strict equality `===` and `!==`."
            })

    elif language in ["C", "C++"]:
        # Buffer Overflow: Unbounded string functions
        unsafe_c_funcs = [
            ("gets", "CRITICAL", "CWE-242", "The `gets()` function does not perform bounds checking and is fundamentally insecure."),
            ("strcpy", "HIGH", "CWE-120", "Unbounded buffer copy with `strcpy()` can lead to stack/heap buffer overflow."),
            ("sprintf", "HIGH", "CWE-134", "`sprintf()` without buffer limits can overflow destination buffers."),
            ("strcat", "MEDIUM", "CWE-120", "`strcat()` can exceed buffer capacity if not strictly bounded.")
        ]
        for func, sev, cwe, desc in unsafe_c_funcs:
            if re.search(rf'\b{func}\s*\(', code):
                issues.append({
                    "title": f"Insecure C-Style String Function: {func}()",
                    "severity": sev,
                    "cwe": cwe,
                    "description": desc,
                    "recommendation": f"Replace with safer alternatives like `snprintf()`, `strncpy()`, or `std::string` in C++."
                })

        # Memory leak check
        alloc_count = len(re.findall(r'\b(malloc|calloc|realloc)\b', code))
        free_count = len(re.findall(r'\bfree\b', code))
        if alloc_count > free_count:
            issues.append({
                "title": "Potential Memory Leak (Unfreed Allocation)",
                "severity": "HIGH",
                "cwe": "CWE-401",
                "description": f"Detected {alloc_count} dynamic allocation(s) but only {free_count} `free()` call(s).",
                "recommendation": "Ensure every allocated pointer is deallocated with `free()` along all exit paths."
            })

        if language == "C++":
            new_count = len(re.findall(r'\bnew\b', code))
            del_count = len(re.findall(r'\bdelete\b', code))
            if new_count > del_count:
                issues.append({
                    "title": "Unmanaged Dynamic Resource in C++",
                    "severity": "MEDIUM",
                    "cwe": "CWE-401",
                    "description": "Detected `new` without corresponding `delete`. Modern C++ encourages RAII and smart pointers.",
                    "recommendation": "Use `std::unique_ptr` or `std::shared_ptr` instead of raw `new` and `delete`."
                })

    elif language == "Java":
        # Java SQL Injection
        if re.search(r'(createStatement|executeQuery)\s*\([^)]*\+', code):
            issues.append({
                "title": "SQL Injection in Java",
                "severity": "CRITICAL",
                "cwe": "CWE-89",
                "description": "Concatenating strings into JDBC statements creates SQL injection vulnerabilities.",
                "recommendation": "Use `PreparedStatement` with parameterized placeholders (`?`)."
            })

        # Unclosed Streams / Resources
        if re.search(r'new\s+(FileInputStream|FileOutputStream|BufferedReader)\b', code) and "try (" not in code and "try(" not in code:
            issues.append({
                "title": "Potential Resource Leak",
                "severity": "MEDIUM",
                "cwe": "CWE-775",
                "description": "Opening file streams without try-with-resources can exhaust file descriptors on error.",
                "recommendation": "Enclose streams in a `try (...)` block to guarantee automatic closure."
            })

    elif language == "SQL":
        upper_code = code.upper()
        # Unconditional DELETE or UPDATE
        if "DELETE FROM" in upper_code and "WHERE" not in upper_code:
            issues.append({
                "title": "Catastrophic Unconditional DELETE",
                "severity": "CRITICAL",
                "cwe": "CWE-284",
                "description": "DELETE statement without a WHERE clause will purge all rows from the table.",
                "recommendation": "Add a specific WHERE clause: `DELETE FROM table WHERE id = ?`."
            })
        if "UPDATE " in upper_code and "WHERE" not in upper_code and "SET " in upper_code:
            issues.append({
                "title": "Unconditional UPDATE Statement",
                "severity": "CRITICAL",
                "cwe": "CWE-284",
                "description": "UPDATE statement without a WHERE clause updates every single row in the table.",
                "recommendation": "Always specify a WHERE condition when updating records."
            })
        if "DROP TABLE" in upper_code or "DROP DATABASE" in upper_code:
            issues.append({
                "title": "Destructive DDL: DROP TABLE / DATABASE",
                "severity": "HIGH",
                "cwe": "CWE-284",
                "description": "Direct drop statement detected. In production, this permanently destroys schema and data.",
                "recommendation": "Use migration tools with backup verification and soft-deletion flags."
            })
        if re.search(r'(?i)GRANT\s+ALL\s+.*?\s+TO\s+.*?[@%]', code):
            issues.append({
                "title": "Overly Permissive Database Privileges",
                "severity": "HIGH",
                "cwe": "CWE-250",
                "description": "Granting ALL PRIVILEGES violates the Principle of Least Privilege.",
                "recommendation": "Grant only required DML permissions (SELECT, INSERT, UPDATE) on specific tables."
            })

    elif language == "MongoDB":
        # MongoDB NoSQL injection via $where
        if "$where" in code:
            issues.append({
                "title": "NoSQL Injection via $where Operator",
                "severity": "CRITICAL",
                "cwe": "CWE-943",
                "description": "The `$where` operator evaluates arbitrary JavaScript expressions inside the database engine, enabling Remote Code Execution (RCE).",
                "recommendation": "Replace `$where` with standard MQL query operators or aggregation expressions (`$expr`)."
            })
        # Plaintext connection string
        if re.search(r'mongodb(\+srv)?:\/\/[a-zA-Z0-9_\-\.]+:[^@\/\s]+@', code):
            issues.append({
                "title": "Hardcoded MongoDB Credentials in URI",
                "severity": "HIGH",
                "cwe": "CWE-798",
                "description": "Database user credentials are embedded directly in the connection URI.",
                "recommendation": "Inject credentials via environment variables or secret vaults (e.g. `process.env.MONGO_URI`)."
            })
        # Unbounded query
        if re.search(r'\.find\(\s*(\{\s*\})?\s*\)(?!\s*\.limit)', code):
            issues.append({
                "title": "Unbounded Query (Missing .limit())",
                "severity": "MEDIUM",
                "cwe": "CWE-400",
                "description": "Querying collections without a `.limit()` clause can cause Denial of Service (OOM) on large datasets.",
                "recommendation": "Always apply pagination with `.limit(n)` and `.skip(n)` or cursor-based range pagination."
            })

    elif language == "Perl":
        # Two-argument open() vulnerability
        if re.search(r'\bopen\s*\(\s*[a-zA-Z0-9_]+\s*,\s*["\']?[<>]?\s*\$', code):
            issues.append({
                "title": "Insecure Two-Argument open() Call",
                "severity": "CRITICAL",
                "cwe": "CWE-78",
                "description": "Classic Perl 2-argument `open()` interprets pipe characters (`|`) in filenames as shell commands, enabling arbitrary command injection.",
                "recommendation": "Always use modern 3-argument open with lexical filehandles: `open(my $fh, '<', $filename) or die $!;`."
            })
        # Missing strict/warnings
        if "use strict;" not in code and "use warnings;" not in code:
            issues.append({
                "title": "Missing `use strict;` / `use warnings;`",
                "severity": "HIGH",
                "cwe": "CWE-698",
                "description": "Perl scripts without `use strict;` and `use warnings;` permit implicit global variables, barewords, and unhandled errors.",
                "recommendation": "Add `use strict;` and `use warnings;` at the very beginning of the Perl script."
            })
        # Insecure string eval
        if re.search(r'\beval\s*["\'].*?\b', code) or re.search(r'\beval\s*\(\s*\$', code):
            issues.append({
                "title": "Arbitrary Code Execution via Perl eval",
                "severity": "CRITICAL",
                "cwe": "CWE-95",
                "description": "Evaluating dynamic string input with `eval` executes untrusted Perl expressions.",
                "recommendation": "Use block `eval { ... }` strictly for exception handling, never evaluate dynamic user strings."
            })

    return issues
