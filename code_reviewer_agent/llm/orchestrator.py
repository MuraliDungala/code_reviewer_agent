"""
Orchestrator Module
Coordinates the entire multi-stage Hybrid AI Code Review Pipeline:
Streamlit UI
→ Orchestrator
→ Language Detection
→ Static AST Analysis
→ Style Checking
→ Security Analysis
→ Code Smell Detection
→ AI/LLM Deep Review
→ Optimization & Complexity
→ Best Practices
→ Test Case Generator
→ Auto-Fix Generator
→ Orchestrator (Merge, Deduplicate, Categorize, Prioritize & Score)
→ Final Report
"""

import os
import re
from typing import Dict, Any, List, Tuple

from llm.langchain_integration import detect_language, run_langchain_review, get_llm
from reviewers.static_reviewer import get_static_findings, static_review
from reviewers.security_reviewer import run_security_analysis
from reviewers.smell_reviewer import run_smell_analysis
from agents.style_agent import check_code_style
from agents.test_generator import generate_unit_tests
from agents.autofix_generator import generate_autofix, compute_unified_diff, compute_line_diff


SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "PHP", "Java",
    "C", "C++", "C#", "Go", "Rust", "Ruby", "Perl",
    "SQL", "MongoDB", "HTML", "CSS", "Bash"
]


def review_code_orchestrated(code: str, language_choice: str = "Auto-Detect") -> Dict[str, Any]:
    """
    Executes the full sequential code review pipeline.
    Merges, deduplicates, categorizes, prioritizes, and computes the 0-100 quality score.
    """
    code_snippet = code.strip()
    if not code_snippet:
        return {
            "error": "No code provided for review.",
            "quality_score": 0,
            "language": "Unknown"
        }

    # -------------------------------------------------------------
    # Stage 1: Language Detection
    # -------------------------------------------------------------
    if language_choice and language_choice != "Auto-Detect":
        language = language_choice
    else:
        language = detect_language(code_snippet)
    if not language or language == "Unknown":
        language = "Python"

    # -------------------------------------------------------------
    # Stage 2: Static AST Analysis
    # -------------------------------------------------------------
    static_findings = get_static_findings(code_snippet, language)

    # -------------------------------------------------------------
    # Stage 3: Style Checking
    # -------------------------------------------------------------
    style_findings = check_code_style(code_snippet, language)

    # -------------------------------------------------------------
    # Stage 4: Security Analysis
    # -------------------------------------------------------------
    security_findings = run_security_analysis(code_snippet, language)

    # -------------------------------------------------------------
    # Stage 5: Code Smell Detection
    # -------------------------------------------------------------
    smell_findings = run_smell_analysis(code_snippet, language)

    # -------------------------------------------------------------
    # Stage 6: AI / LLM Deep Review
    # -------------------------------------------------------------
    ai_raw_report, detected_lang_display = run_langchain_review(
        code=code_snippet,
        language_choice=language,
        static_findings=static_findings,
        security_findings=security_findings
    )

    # Parse AI response sections
    ai_parsed = _parse_ai_report(ai_raw_report, language)

    # -------------------------------------------------------------
    # Stage 7: Optimization & Complexity Analysis
    # -------------------------------------------------------------
    time_complexity = ai_parsed.get("time_complexity", "O(N)")
    space_complexity = ai_parsed.get("space_complexity", "O(1)")
    complexity_explanation = ai_parsed.get("complexity_explanation", "Analyzed based on algorithmic structure and memory allocation.")

    # -------------------------------------------------------------
    # Stage 8: Best Practices Extraction
    # -------------------------------------------------------------
    best_practices = ai_parsed.get("best_practices", [
        f"Adhere to standard {language} idioms and style guidelines.",
        "Include unit tests and input validation for boundary cases.",
        "Ensure dynamic resources and connections are properly handled."
    ])

    # -------------------------------------------------------------
    # Stage 9: Test Case Generator
    # -------------------------------------------------------------
    test_cases = ai_parsed.get("test_cases", "")
    if not test_cases or len(test_cases) < 30:
        from agents.test_generator import _generate_fallback_tests, FRAMEWORK_MAP
        framework = FRAMEWORK_MAP.get(language, "Standard Unit Tests")
        test_cases = _generate_fallback_tests(code_snippet, language, framework)

    # -------------------------------------------------------------
    # Stage 10: Auto-Fix Generator & Diff
    # -------------------------------------------------------------
    suggested_fix = ai_parsed.get("optimized_code", "")
    if not suggested_fix or len(suggested_fix) < 15 or suggested_fix == code_snippet:
        from agents.autofix_generator import _fallback_fix
        suggested_fix = _fallback_fix(code_snippet, language)

    unified_diff = compute_unified_diff(code_snippet, suggested_fix)
    line_diff = compute_line_diff(code_snippet, suggested_fix)

    # -------------------------------------------------------------
    # Stage 11: Orchestrator Merge, Deduplicate, Categorize & Prioritize
    # -------------------------------------------------------------
    merged_bugs, merged_security, merged_smells, merged_styles = _merge_and_deduplicate(
        static_findings=static_findings,
        security_findings=security_findings,
        smell_findings=smell_findings,
        style_findings=style_findings,
        ai_bugs=ai_parsed.get("bugs", []),
        ai_security=ai_parsed.get("security", []),
        ai_smells=ai_parsed.get("smells", [])
    )

    # -------------------------------------------------------------
    # Stage 12: Code Quality Scoring System (0-100)
    # -------------------------------------------------------------
    scores_data = _calculate_quality_score(
        bugs=merged_bugs,
        security=merged_security,
        smells=merged_smells,
        styles=merged_styles,
        time_complexity=time_complexity
    )

    # -------------------------------------------------------------
    # Stage 13: Final Report Assembly
    # -------------------------------------------------------------
    final_report = {
        "language": language,
        "language_display": detected_lang_display,
        "quality_score": scores_data["overall_score"],
        "has_fatal_syntax": scores_data.get("has_fatal_syntax", False),
        "sub_scores": {
            "security": scores_data["security_score"],
            "maintainability": scores_data["maintainability_score"],
            "performance": scores_data["performance_score"]
        },
        "severity_counts": scores_data["severity_counts"],
        "executive_summary": ai_parsed.get("executive_summary", "Review complete. See detailed diagnostic tabs below."),
        "bugs": merged_bugs,
        "security_issues": merged_security,
        "code_smells": merged_smells,
        "style_issues": merged_styles,
        "logic_issues": merged_bugs,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "complexity_explanation": complexity_explanation,
        "performance_notes": ai_parsed.get("performance_notes", []),
        "best_practices": best_practices,
        "suggested_fix": suggested_fix,
        "unified_diff": unified_diff,
        "line_diff": line_diff,
        "test_cases": test_cases,
        "raw_ai_report": ai_raw_report,
        "markdown_report": _build_markdown_report(
            language=language,
            quality_score=scores_data["overall_score"],
            sub_scores=scores_data,
            severity_counts=scores_data["severity_counts"],
            bugs=merged_bugs,
            security=merged_security,
            smells=merged_smells,
            styles=merged_styles,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            best_practices=best_practices,
            suggested_fix=suggested_fix,
            test_cases=test_cases
        )
    }

    return final_report


def _merge_and_deduplicate(
    static_findings: List[Dict[str, Any]],
    security_findings: List[Dict[str, Any]],
    smell_findings: List[Dict[str, Any]],
    style_findings: List[Dict[str, Any]],
    ai_bugs: List[Dict[str, Any]],
    ai_security: List[Dict[str, Any]] = None,
    ai_smells: List[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Merges findings from static, security, smell, and AI agents.
    Removes redundant duplicates while preserving and enriching all distinct error findings.
    """
    merged_bugs: List[Dict[str, Any]] = []
    merged_security: List[Dict[str, Any]] = []
    merged_smells: List[Dict[str, Any]] = []
    merged_styles: List[Dict[str, Any]] = []

    seen_map: Dict[str, Dict[str, Any]] = {}

    def get_sig(issue: Dict[str, Any]) -> str:
        title = issue.get("title", "")
        line = str(issue.get("line", ""))
        desc = issue.get("description", "")

        # Clean title: strip [HIGH], [CRITICAL], (Line X), etc.
        norm_title = re.sub(r'^\[?(?:CRITICAL|HIGH|MEDIUM|LOW)\]?\s*[:-]?\s*', '', title, flags=re.IGNORECASE).strip()
        norm_title = re.sub(r'\(Line\s*\d+\)', '', norm_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', norm_title.lower())

        # If title is generic, use description prefix
        if len(clean_title) < 6 or clean_title in ["issue", "flaw", "bug", "codeflaw", "logicflaw", "error", "reportflaw"]:
            clean_desc = re.sub(r'[^a-zA-Z0-9]', '', desc.lower())[:25]
            return f"{clean_title}_{line}_{clean_desc}"

        return clean_title

    def add_issue(issue: Dict[str, Any], target_list: List[Dict[str, Any]]):
        sig = get_sig(issue)

        matched = seen_map.get(sig)
        if matched is not None:
            # Merge richer attributes
            if not matched.get("line") and issue.get("line"):
                matched["line"] = issue["line"]
            if not matched.get("column") and issue.get("column"):
                matched["column"] = issue["column"]
            if not matched.get("code_snippet") and issue.get("code_snippet"):
                matched["code_snippet"] = issue["code_snippet"]
            if len(issue.get("recommendation", "")) > len(matched.get("recommendation", "")):
                matched["recommendation"] = issue["recommendation"]
            if len(issue.get("description", "")) > len(matched.get("description", "")) + 15:
                matched["description"] = issue["description"]
        else:
            seen_map[sig] = issue
            target_list.append(issue)

    # 1. Security findings from static engine
    for sec in security_findings:
        add_issue(sec, merged_security)

    # 2. AI Security findings
    if ai_security:
        for ai_s in ai_security:
            add_issue(ai_s, merged_security)

    # 3. Static syntax and bug findings (AST)
    for bug in static_findings:
        if bug.get("severity") in ["CRITICAL", "HIGH"] and any(k in bug.get("title", "").upper() for k in ["DELETE", "UPDATE", "SQL", "$WHERE"]):
            add_issue(bug, merged_security)
        else:
            add_issue(bug, merged_bugs)

    # 4. AI Bugs
    for ai_b in ai_bugs:
        add_issue(ai_b, merged_bugs)

    # 5. Code smells from static engine
    for smell in smell_findings:
        add_issue(smell, merged_smells)

    # 6. AI Code smells
    if ai_smells:
        for ai_sm in ai_smells:
            add_issue(ai_sm, merged_smells)

    # 7. Style violations
    for sty in style_findings:
        rule_name = sty.get("rule", "")
        sig = re.sub(r'[^a-zA-Z0-9]', '', rule_name.lower())[:25]
        if sig not in seen_map:
            seen_map[sig] = sty
            merged_styles.append(sty)

    return merged_bugs, merged_security, merged_smells, merged_styles


def _calculate_quality_score(bugs, security, smells, styles, time_complexity) -> Dict[str, Any]:
    """
    Calculates the 0-100 overall code quality score and sub-scores.
    Caps score realistically when critical syntax errors prevent compilation/execution.
    """
    all_issues = []
    has_fatal_syntax = False

    for b in bugs:
        sev = b.get("severity", "HIGH")
        all_issues.append(sev)
        title_lower = b.get("title", "").lower()
        if any(term in title_lower for term in ["syntax", "syntaxerror", "indentationerror", "unmatched", "mismatched"]):
            has_fatal_syntax = True

    for s in security:
        all_issues.append(s.get("severity", "HIGH"))
    for sm in smells:
        all_issues.append(sm.get("severity", "MEDIUM"))
    for st in styles:
        all_issues.append(st.get("severity", "LOW"))

    severity_counts = {
        "CRITICAL": all_issues.count("CRITICAL"),
        "HIGH": all_issues.count("HIGH"),
        "MEDIUM": all_issues.count("MEDIUM"),
        "LOW": all_issues.count("LOW")
    }

    # Deductions
    deduction = (
        severity_counts["CRITICAL"] * 30 +
        severity_counts["HIGH"] * 15 +
        severity_counts["MEDIUM"] * 8 +
        severity_counts["LOW"] * 3
    )
    overall_score = max(0, min(100, 100 - deduction))

    # Capping if fatal or critical bugs exist
    if has_fatal_syntax:
        overall_score = min(overall_score, 15)
    elif severity_counts["CRITICAL"] >= 2:
        overall_score = min(overall_score, 35)
    elif severity_counts["CRITICAL"] >= 1:
        overall_score = min(overall_score, 50)

    # Security sub-score
    sec_crit = sum(1 for s in security if s.get("severity") == "CRITICAL")
    sec_high = sum(1 for s in security if s.get("severity") == "HIGH")
    sec_med = sum(1 for s in security if s.get("severity") == "MEDIUM")
    security_score = max(0, min(100, 100 - (sec_crit * 35 + sec_high * 20 + sec_med * 10)))

    # Maintainability sub-score
    maintainability_score = max(0, min(100, 100 - (len(smells) * 12 + len(styles) * 5)))

    # Performance sub-score
    perf_penalty = 0
    if any(n in time_complexity for n in ["N^2", "N^3", "2^N", "N!"]):
        perf_penalty += 25
    performance_score = max(0, min(100, 100 - perf_penalty))

    return {
        "overall_score": overall_score,
        "security_score": security_score,
        "maintainability_score": maintainability_score,
        "performance_score": performance_score,
        "severity_counts": severity_counts,
        "has_fatal_syntax": has_fatal_syntax
    }


def _parse_bullet_items(text: str) -> List[Dict[str, Any]]:
    """
    Parses bulleted or numbered items into structured issue dictionaries.
    Extracts Severity, Title, Description, and Recommendation cleanly.
    """
    items = []
    if not text:
        return items

    # Split into bullet/numbered items
    blocks = re.split(r'\n(?=(?:[\s]*[-*]|\s*\d+[\.)])\s+)', text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Verify that this block actually begins with a bullet marker or list number
        if not re.match(r'^(?:[\s]*[-*]|\s*\d+[\.)])\s+', block):
            continue

        cleaned = re.sub(r'^(?:[\s]*[-*]|\s*\d+[\.)])\s+', '', block).strip()
        if not cleaned:
            continue

        # Extract Severity if present
        severity = "HIGH"
        sev_match = re.search(r'\[Severity:\s*(CRITICAL|HIGH|MEDIUM|LOW)\]', cleaned, re.IGNORECASE)
        if sev_match:
            severity = sev_match.group(1).upper()
            cleaned = re.sub(r'\[Severity:\s*(?:CRITICAL|HIGH|MEDIUM|LOW)\]\s*', '', cleaned, flags=re.IGNORECASE).strip()
        else:
            lower_clean = cleaned.lower()
            if any(w in lower_clean for w in ["critical", "fatal", "syntaxerror", "syntax error", "zerodivision", "division by zero"]):
                severity = "CRITICAL"
            elif any(w in lower_clean for w in ["warning", "style", "convention", "pep8", "naming"]):
                severity = "LOW"
            elif any(w in lower_clean for w in ["smell", "magic number", "complexity", "redundant", "nested"]):
                severity = "MEDIUM"

        # Extract Recommendation if present
        rec = "Review and apply suggested fixes."
        rec_match = re.search(r'(?i)\*?(?:Recommendation|Fix|Resolution|Remediation):\*?\s*(.+)$', cleaned, re.DOTALL)
        if rec_match:
            rec = rec_match.group(1).strip().strip("*_ ")
            cleaned = cleaned[:rec_match.start()].strip()

        # Extract Title and Description
        title = "Issue"
        title_match = re.search(r'^\*\*([^*]+)\*\*[:\s-]*', cleaned)
        if title_match:
            title = title_match.group(1).strip()
            desc = cleaned[title_match.end():].strip()
        else:
            colon_idx = cleaned.find(":")
            if 0 < colon_idx < 60:
                title = cleaned[:colon_idx].strip("*_ ")
                desc = cleaned[colon_idx + 1:].strip()
            else:
                title = cleaned[:45].strip() + ("..." if len(cleaned) > 45 else "")
                desc = cleaned

        # Clean title
        title = re.sub(r'^\d+[\.\)]\s*', '', title).strip("*_ ")
        title = re.sub(r'^\[?(?:CRITICAL|HIGH|MEDIUM|LOW)\]?\s*[:-]?\s*', '', title, flags=re.IGNORECASE).strip()
        title = re.sub(r'\(Line\s*\d+\)', '', title, flags=re.IGNORECASE).strip()
        title = title.strip("*_ ")

        # Clean desc
        desc = re.sub(r'^\s*[:-]\s*', '', desc).strip()
        if not desc:
            desc = title

        items.append({
            "title": title,
            "severity": severity,
            "description": desc,
            "recommendation": rec
        })

    return items


def _parse_ai_report(report_text: str, language: str) -> Dict[str, Any]:
    """
    Parses sections from the AI review response.
    Extracts Bugs, Complexities, Security Vulnerabilities, Smells, Best Practices, Code, and Tests.
    """
    parsed = {
        "executive_summary": "",
        "bugs": [],
        "security": [],
        "smells": [],
        "time_complexity": "O(N)",
        "space_complexity": "O(1)",
        "complexity_explanation": "",
        "performance_notes": [],
        "best_practices": [],
        "optimized_code": "",
        "test_cases": ""
    }

    if not report_text:
        return parsed

    def _extract_section(header_regex: str, next_regex: str = r'\n###|\Z') -> str:
        m = re.search(rf'###\s*[\d\.]*\s*{header_regex}[^\n]*\n(.*?)(?={next_regex})', report_text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _extract_code(text: str) -> str:
        m = re.search(r'```(?:[a-zA-Z0-9_\-\+]*)\n(.*?)```', text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()

    # Section 1: Code Understanding & Logic Bugs
    bugs_sec = _extract_section(r'Code Understanding', r'\n###\s*[\d\.]*\s*Time|\Z')
    if bugs_sec:
        # Separate narrative paragraph from bullet items
        parts = re.split(r'\n(?=(?:[\s]*[-*]|\s*\d+[\.)])\s+)', bugs_sec, maxsplit=1)
        parsed["executive_summary"] = parts[0].strip()
        if len(parts) > 1:
            parsed["bugs"] = _parse_bullet_items(parts[1])
        else:
            # Fallback if no bullets: check if text describes an error
            lower_sec = bugs_sec.lower()
            if any(term in lower_sec for term in ["syntax error", "error", "bug", "crash", "flaw", "exception"]):
                parsed["bugs"].append({
                    "title": "Reported Code Flaw",
                    "severity": "HIGH",
                    "description": bugs_sec[:300].strip(),
                    "recommendation": "Review the logic and correct errors outlined above."
                })

    # Section 2: Time & Space Complexity
    comp_sec = _extract_section(r'Time & Space Complexity', r'\n###\s*[\d\.]*\s*Security|\Z')
    if comp_sec:
        parsed["complexity_explanation"] = comp_sec
        t_match = re.search(r'Time Complexity:?\s*\*?\*?([O\(\)\w\s\^\+\*\.\/]+)\*?\*?', comp_sec, re.IGNORECASE)
        if t_match:
            parsed["time_complexity"] = t_match.group(1).strip()
        s_match = re.search(r'Space Complexity:?\s*\*?\*?([O\(\)\w\s\^\+\*\.\/]+)\*?\*?', comp_sec, re.IGNORECASE)
        if s_match:
            parsed["space_complexity"] = s_match.group(1).strip()

    # Section 3: Security Vulnerabilities & Code Smells
    sec_smell_sec = _extract_section(r'Security Vulnerabilities', r'\n###\s*[\d\.]*\s*Performance|\Z')
    if sec_smell_sec:
        sec_smell_items = _parse_bullet_items(sec_smell_sec)
        for item in sec_smell_items:
            lower_text = (item["title"] + " " + item["description"]).lower()
            if any(term in lower_text for term in [
                "injection", "xss", "buffer", "overflow", "cwe", "secret", "password",
                "token", "rce", "deserialization", "csrf", "untrusted", "vulnerability",
                "permission", "privilege", "leak", "exploit"
            ]):
                parsed["security"].append(item)
            elif any(term in lower_text for term in [
                "smell", "debt", "dead code", "unused", "redundant", "magic number",
                "complexity", "duplicate", "coupling", "naming", "convention", "readability"
            ]):
                parsed["smells"].append(item)
            else:
                if item["severity"] in ["CRITICAL", "HIGH"]:
                    parsed["bugs"].append(item)
                else:
                    parsed["smells"].append(item)

    # Section 4: Performance & Best Practices
    bp_sec = _extract_section(r'Performance & Best Practices', r'\n###\s*[\d\.]*\s*Optimized|\Z')
    if bp_sec:
        bps = re.findall(r'[-*]\s*(.+)', bp_sec)
        parsed["best_practices"] = [b.strip() for b in bps if b.strip()] if bps else [bp_sec.strip()]

    # Section 5: Optimized Code
    opt_sec = _extract_section(r'Optimized Code', r'\n###\s*[\d\.]*\s*Unit Test|\Z')
    if opt_sec:
        parsed["optimized_code"] = _extract_code(opt_sec)

    # Section 6: Unit Test Cases
    test_sec = _extract_section(r'Unit Test', r'\Z')
    if test_sec:
        parsed["test_cases"] = _extract_code(test_sec)

    return parsed


def _build_markdown_report(language, quality_score, sub_scores, severity_counts,
                           bugs, security, smells, styles, time_complexity,
                           space_complexity, best_practices, suggested_fix, test_cases) -> str:
    """Builds an exportable, comprehensive markdown review report."""
    md = f"""# 🛡️ AI Agent Code Review Report

**Programming Language:** {language}  
**Overall Code Quality Score:** **{quality_score}/100**  
**Sub-Scores:** Security: `{sub_scores['security_score']}/100` | Maintainability: `{sub_scores['maintainability_score']}/100` | Performance: `{sub_scores['performance_score']}/100`

---

## 📊 Severity Distribution
- 🚨 **Critical:** {severity_counts['CRITICAL']}
- ⚠️ **High Priority:** {severity_counts['HIGH']}
- 💡 **Medium Priority:** {severity_counts['MEDIUM']}
- ℹ️ **Low / Style:** {severity_counts['LOW']}

---

## 🐛 Logic Flaws & Syntax Errors ({len(bugs)})
"""
    if not bugs:
        md += "✅ No logic flaws or syntax errors detected.\n\n"
    else:
        for b in bugs:
            line_str = f" [Line {b['line']}]" if b.get('line') else ""
            md += f"### [{b.get('severity', 'HIGH')}]{line_str} {b.get('title')}\n"
            md += f"- **Description:** {b.get('description')}\n"
            md += f"- **Resolution:** {b.get('recommendation')}\n\n"

    md += f"""---

## 🛡️ Security Vulnerabilities ({len(security)})
"""
    if not security:
        md += "✅ No critical security vulnerabilities detected.\n\n"
    else:
        for s in security:
            cwe = f" ({s['cwe']})" if s.get('cwe') else ""
            md += f"### [{s.get('severity', 'HIGH')}]{cwe} {s.get('title')}\n"
            md += f"- **Description:** {s.get('description')}\n"
            md += f"- **Remediation:** {s.get('recommendation')}\n\n"

    md += f"""---

## 🧹 Code Smells & Style ({len(smells) + len(styles)})
"""
    for sm in smells:
        md += f"- **[Code Smell] {sm.get('title')}:** {sm.get('description')} (*Fix:* {sm.get('recommendation')})\n"
    for st in styles:
        md += f"- **[Style] {st.get('rule')}:** {st.get('description')}\n"

    md += f"""

---

## ⏱️ Algorithmic Complexity
- **Time Complexity:** `{time_complexity}`
- **Space Complexity:** `{space_complexity}`

---

## 💡 Best Practice Recommendations
"""
    for bp in best_practices:
        md += f"- {bp}\n"

    md += f"""

---

## 🔄 Corrected & Optimized Code
```{language.lower()}
{suggested_fix}
```

---

## 🧪 Generated Unit Test Suite
```{language.lower()}
{test_cases}
```
"""
    return md
