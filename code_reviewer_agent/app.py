import streamlit as st
import os
import importlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dynamic module reload to ensure zero stale cache
import llm.orchestrator
import llm.langchain_integration
import reviewers.security_reviewer
import reviewers.smell_reviewer
import reviewers.static_reviewer
import agents.style_agent
import agents.test_generator
import agents.autofix_generator

importlib.reload(llm.orchestrator)
importlib.reload(llm.langchain_integration)
importlib.reload(reviewers.security_reviewer)
importlib.reload(reviewers.smell_reviewer)
importlib.reload(reviewers.static_reviewer)
importlib.reload(agents.style_agent)
importlib.reload(agents.test_generator)
importlib.reload(agents.autofix_generator)

from llm.orchestrator import review_code_orchestrated


# -------------------------------------------------------------
# Streamlit Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="NexReview AI | Intelligent Multi-Engine Code Reviewer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Premium Aesthetics & Design System (CSS)
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Ambient Background Glow */
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(79, 70, 229, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 85% 25%, rgba(6, 182, 212, 0.06) 0%, transparent 45%),
                    radial-gradient(circle at 50% 85%, rgba(236, 72, 153, 0.05) 0%, transparent 50%),
                    #0B0F19;
    }

    /* Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 32px 36px;
        margin-bottom: 28px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(16px);
        position: relative;
        overflow: hidden;
    }

    .hero-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6, #EC4899, #10B981);
    }

    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 20%, #CBD5E1 70%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .hero-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        font-weight: 400;
        max-width: 820px;
        line-height: 1.6;
        margin-bottom: 16px;
    }

    .pill-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        background: rgba(99, 102, 241, 0.15);
        color: #A5B4FC;
        border: 1px solid rgba(99, 102, 241, 0.3);
        margin-right: 8px;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Metric Glass Cards */
    .metric-card-pro {
        background: linear-gradient(145deg, rgba(26, 32, 53, 0.8) 0%, rgba(15, 23, 42, 0.7) 100%);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        padding: 22px 20px;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        backdrop-filter: blur(12px);
    }
    .metric-card-pro:hover {
        transform: translateY(-3px);
        border-color: rgba(255, 255, 255, 0.16);
        box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.6);
    }

    .metric-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 6px;
    }

    .score-excellent-glow {
        color: #10B981;
        font-size: 2.8rem;
        font-weight: 800;
        text-shadow: 0 0 25px rgba(16, 185, 129, 0.4);
    }
    .score-warning-glow {
        color: #F59E0B;
        font-size: 2.8rem;
        font-weight: 800;
        text-shadow: 0 0 25px rgba(245, 158, 11, 0.4);
    }
    .score-danger-glow {
        color: #F43F5E;
        font-size: 2.8rem;
        font-weight: 800;
        text-shadow: 0 0 25px rgba(244, 63, 94, 0.4);
    }

    /* Severity Badges */
    .sev-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.78rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .sev-critical { background: rgba(244, 63, 94, 0.15); color: #FDA4AF; border: 1px solid rgba(244, 63, 94, 0.4); }
    .sev-high { background: rgba(249, 115, 22, 0.15); color: #FDBA74; border: 1px solid rgba(249, 115, 22, 0.4); }
    .sev-medium { background: rgba(234, 179, 8, 0.15); color: #FDE047; border: 1px solid rgba(234, 179, 8, 0.4); }
    .sev-low { background: rgba(59, 130, 246, 0.15); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.4); }

    /* Issue Box Cards */
    .issue-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .issue-card:hover {
        background: rgba(30, 41, 59, 0.7);
        border-color: rgba(255, 255, 255, 0.12);
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0B0F19;
    }
    ::-webkit-scrollbar-thumb {
        background: #1E293B;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Sidebar Configuration & Language Presets
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ **Control Deck**")

    # Live Connection Status
    api_ready = bool(os.getenv("GROQ_API_KEY"))
    status_color = "#10B981" if api_ready else "#F43F5E"
    status_text = "Groq LPU Connected" if api_ready else "Missing GROQ_API_KEY"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; padding:8px 12px; background:rgba(255,255,255,0.03); border-radius:8px; border:1px solid rgba(255,255,255,0.06); margin-bottom:16px;">
        <span style="width:8px; height:8px; border-radius:50%; background:{status_color};"></span>
        <span style="font-size:0.85rem; color:#E2E8F0; font-weight:600;">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🎯 **Target Language**")
    lang_choice = st.selectbox(
        "Select Language",
        options=[
            "Auto-Detect",
            "SQL",
            "MongoDB",
            "Perl",
            "Python",
            "JavaScript",
            "TypeScript",
            "PHP",
            "Java",
            "C",
            "C++",
            "C#",
            "Go",
            "Rust",
            "Ruby",
            "HTML/CSS"
        ],
        index=0,
        label_visibility="collapsed",
        help="Choose Auto-Detect or explicitly target a language runtime."
    )

    st.markdown("---")
    st.markdown("#### 📦 **Quick Load Sample**")

    sample_choice = st.selectbox(
        "Load a vulnerable/smelly snippet:",
        options=[
            "Custom Code (Empty)",
            "🗄️ SQL: Unindexed Cartesian Join & DELETE",
            "🍃 MongoDB: NoSQL $where Injection",
            "🐪 Perl: Two-Argument open() Vulnerability",
            "🐘 PHP: Zero Division & Broken Scope",
            "⚡ JavaScript: DOM XSS & Loose Coercion",
            "🐍 Python: Dynamic SQL Injection",
            "⚙️ C: Unbounded Buffer Overflow",
            "☕ Java: Resource Leak & Concatenation"
        ]
    )

    sample_codes = {
        "🗄️ SQL: Unindexed Cartesian Join & DELETE": """-- Critical: Unconditional DELETE + Wildcard Join
DELETE FROM audit_logs;

SELECT * 
FROM users u, transactions t, accounts a
WHERE u.status = 'active'
ORDER BY t.created_at DESC;
""",
        "🍃 MongoDB: NoSQL $where Injection": """// NoSQL Injection via $where + Unbounded Query
const targetName = req.body.username;

db.users.find({
    $where: "this.username == '" + targetName + "'"
});

// Dangerous unbounded fetch
const allRecords = db.audit_trails.find({});
""",
        "🐪 Perl: Two-Argument open() Vulnerability": """#!/usr/bin/perl
# Insecure 2-arg open() permits pipe command injection

sub read_user_file {
    my ($file) = @_;
    
    # Bug: 2-arg open allows "| rm -rf /" shell execution
    open(FILE, "< $file") or die "Cannot open: $!";
    
    while (<FILE>) {
        print $_;
    }
    close(FILE);
}

read_user_file("data.txt");
""",
        "🐘 PHP: Zero Division & Broken Scope": """<?php
$numbers = [10, 20, 30, 40, 50];

for ($i = 0; $i < count($numbers); $i++) {
    $total += $numbers[$i];
}

$average = $total / 0;

echo "Average: " . calculateAverage($numbers);
?>""",
        "⚡ JavaScript: DOM XSS & Loose Coercion": """// DOM XSS via innerHTML and loose equality
function renderUserProfile(userData) {
    const userRole = userData.role;
    
    // Loose equality hazard
    if (userRole == "admin") {
        document.getElementById("badge").innerHTML = "<b>" + userData.name + "</b>";
    }
    
    let total = 0;
    let avg = total / 0;
    console.log("Average:", avg);
}
""",
        "🐍 Python: Dynamic SQL Injection": """import sqlite3

def fetch_user_record(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # High Risk: Dynamic f-string allows SQL injection
    query = f"SELECT id, username, email FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
""",
        "⚙️ C: Unbounded Buffer Overflow": """#include <stdio.h>
#include <string.h>

void execute_task(char *input_str) {
    char local_buf[16];
    // Dangerous: gets and strcpy lack bounds checking
    strcpy(local_buf, input_str);
    printf("Result: %s\\n", local_buf);
}

int main() {
    execute_task("This string exceeds sixteen bytes limit!");
    return 0;
}
""",
        "☕ Java: Resource Leak & Concatenation": """import java.io.*;

public class FileParser {
    public void dumpFile(String path) throws IOException {
        // Resource leak: unclosed stream without try-with-resources
        BufferedReader reader = new BufferedReader(new FileReader(path));
        String line = reader.readLine();
        System.out.println("First line: " + line);
    }
}"""
    }

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#64748B; line-height:1.5;">
        <strong>Multi-Engine Pipeline:</strong><br>
        1. Multi-Language Detection<br>
        2. AST & Static Analysis<br>
        3. Style & Standard Auditing<br>
        4. Security Vulnerability Scan<br>
        5. Code Smell & Debt Engine<br>
        6. Senior AI Peer Review<br>
        7. Algorithmic Complexity (Big-O)<br>
        8. Automated Unit Test Generator<br>
        9. Auto-Fix & Diff Synthesis<br>
        10. 0-100 Quality Score Index
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------------
# Hero Banner
# -------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <span class="pill-tag"><span class="pulse-dot"></span> Pipeline Ready</span>
        <span class="pill-tag" style="background:rgba(16,185,129,0.12); color:#6EE7B7; border-color:rgba(16,185,129,0.3);">Multi-Language Engine</span>
        <span class="pill-tag" style="background:rgba(244,63,94,0.12); color:#FDA4AF; border-color:rgba(244,63,94,0.3);">CWE Security Audit</span>
    </div>
    <h1 class="hero-title">⚡ NexReview AI Agent</h1>
    <p class="hero-subtitle">
        Enterprise-grade code reviewer combining deep static analysis, security vulnerability auditing, 
        code smell diagnostics, algorithmic complexity modeling, and automated test & fix generation.
    </p>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">SQL</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">MongoDB</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">Perl</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">Python</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">JavaScript</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">PHP</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">Java</span>
        <span style="font-size:0.78rem; padding:3px 10px; border-radius:6px; background:rgba(255,255,255,0.05); color:#94A3B8;">C / C++</span>
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Input Area
# -------------------------------------------------------------
initial_snippet = sample_codes.get(sample_choice, "") if sample_choice != "Custom Code (Empty)" else ""

code_input = st.text_area(
    "Source Code Editor",
    value=initial_snippet,
    height=260,
    placeholder="Paste code snippet here (SQL, MongoDB, Perl, Python, JS, PHP, Java, C, C++, etc.)...",
    help="Paste or select a sample snippet from the sidebar."
)

btn_c1, btn_c2 = st.columns([3, 7])
with btn_c1:
    run_btn = st.button("🚀 Run Comprehensive Review", type="primary", use_container_width=True)


# -------------------------------------------------------------
# Execution Flow
# -------------------------------------------------------------
if run_btn:
    if not code_input.strip():
        st.warning("⚠️ Please provide source code before initiating review.")
    else:
        with st.spinner("🤖 Orchestrating review pipeline (Static ➔ Security ➔ Smells ➔ AI ➔ Auto-Fix)..."):
            report = review_code_orchestrated(code_input, lang_choice)

        if "error" in report and report["error"]:
            st.error(report["error"])
        else:
            st.session_state["last_report"] = report

if "last_report" in st.session_state:
    report = st.session_state["last_report"]
    quality_score = report["quality_score"]
    sub_scores = report["sub_scores"]
    severity_counts = report["severity_counts"]
    detected_lang = report["language_display"]
    has_fatal_syntax = report.get("has_fatal_syntax", False)

    st.markdown("<br>", unsafe_allow_html=True)

    # Critical Flaws Alert Banner
    if has_fatal_syntax or severity_counts.get("CRITICAL", 0) > 0:
        st.markdown("""
        <div style="background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.4); border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; display:flex; align-items:center; gap:14px;">
            <span style="font-size: 1.8rem;">🚨</span>
            <div>
                <strong style="color: #FDA4AF; font-size: 1.05rem;">Critical Flaws Detected</strong>
                <div style="color: #CBD5E1; font-size: 0.9rem; margin-top:2px;">
                    The submitted code contains critical syntax errors or fatal runtime flaws that prevent execution. Check the <strong>Logic & Bugs</strong> and <strong>Auto-Fix & Diff</strong> tabs for details and corrected code.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Executive Metrics Header
    # -------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if quality_score >= 85:
            score_class = "score-excellent-glow"
            score_badge = "<span class='sev-badge' style='background:rgba(16,185,129,0.2); color:#6EE7B7; border:1px solid #10B981;'>🟢 Production Ready</span>"
        elif quality_score >= 60:
            score_class = "score-warning-glow"
            score_badge = "<span class='sev-badge' style='background:rgba(245,158,11,0.2); color:#FDE047; border:1px solid #F59E0B;'>🟡 Needs Remediation</span>"
        else:
            score_class = "score-danger-glow"
            score_badge = "<span class='sev-badge' style='background:rgba(244,63,94,0.2); color:#FDA4AF; border:1px solid #F43F5E;'>🔴 Critical Risk</span>"

        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="metric-label">Quality Score</div>
            <div class="{score_class}">{quality_score}<span style="font-size:1.1rem; font-weight:500; color:#64748B;">/100</span></div>
            <div style="margin-top:6px;">{score_badge}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="metric-label">Language & Runtime</div>
            <div style="font-size:2.1rem; font-weight:800; color:#38BDF8; margin:6px 0;">{report['language']}</div>
            <div style="font-size:0.85rem; color:#A7F3D0;">{detected_lang}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="metric-label">Time Complexity</div>
            <div style="font-size:2.0rem; font-weight:800; color:#C084FC; margin:6px 0;">{report['time_complexity']}</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Algorithmic Scaling</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="metric-label">Space Complexity</div>
            <div style="font-size:2.0rem; font-weight:800; color:#2DD4BF; margin:6px 0;">{report['space_complexity']}</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Memory Footprint</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Sub-Score Progress Bars & Severity Counters
    # -------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"**Security Index:** `{sub_scores['security']}/100`")
        st.progress(sub_scores['security'] / 100)
    with sc2:
        st.markdown(f"**Maintainability Index:** `{sub_scores['maintainability']}/100`")
        st.progress(sub_scores['maintainability'] / 100)
    with sc3:
        st.markdown(f"**Performance Index:** `{sub_scores['performance']}/100`")
        st.progress(sub_scores['performance'] / 100)

    st.markdown("<br>", unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(f"<span class='sev-badge sev-critical'>🚨 Critical ({severity_counts['CRITICAL']})</span>", unsafe_allow_html=True)
    with p2:
        st.markdown(f"<span class='sev-badge sev-high'>⚠️ High Priority ({severity_counts['HIGH']})</span>", unsafe_allow_html=True)
    with p3:
        st.markdown(f"<span class='sev-badge sev-medium'>💡 Medium ({severity_counts['MEDIUM']})</span>", unsafe_allow_html=True)
    with p4:
        st.markdown(f"<span class='sev-badge sev-low'>ℹ️ Style / Low ({severity_counts['LOW']})</span>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Multi-Tab Deep Dive
    # -------------------------------------------------------------
    st.markdown("---")
    tab_overview, tab_sec, tab_bugs, tab_smells, tab_diff, tab_tests, tab_bp, tab_export = st.tabs([
        "📊 Executive Summary",
        f"🛡️ Security Vulnerabilities ({len(report['security_issues'])})",
        f"🐛 Logic & Bugs ({len(report['bugs'])})",
        f"🧹 Code Smells & Style ({len(report['code_smells']) + len(report['style_issues'])})",
        "🔄 Auto-Fix & Diff",
        "🧪 Unit Tests",
        "💡 Best Practices",
        "📥 Export Report"
    ])

    # Tab 1: Executive Overview & Complexity
    with tab_overview:
        st.markdown("### 📋 Executive Summary")
        st.info(report["executive_summary"])

        st.markdown("### ⏱️ Algorithmic Complexity Breakdown")
        comp_c1, comp_c2 = st.columns(2)
        with comp_c1:
            st.markdown(f"""
            <div class="issue-card" style="border-left: 4px solid #C084FC;">
                <div style="font-weight:700; color:#E2E8F0; margin-bottom:4px;">⏱️ Time Complexity</div>
                <div style="font-size:1.4rem; font-weight:800; color:#C084FC;">{report['time_complexity']}</div>
            </div>
            """, unsafe_allow_html=True)
        with comp_c2:
            st.markdown(f"""
            <div class="issue-card" style="border-left: 4px solid #2DD4BF;">
                <div style="font-weight:700; color:#E2E8F0; margin-bottom:4px;">💾 Space Complexity</div>
                <div style="font-size:1.4rem; font-weight:800; color:#2DD4BF;">{report['space_complexity']}</div>
            </div>
            """, unsafe_allow_html=True)

        if report.get("complexity_explanation"):
            st.markdown("**Detailed Complexity Rationale:**")
            st.write(report["complexity_explanation"])

    # Tab 2: Security Vulnerabilities
    with tab_sec:
        st.markdown("### 🛡️ Security Vulnerability Audit")
        if not report["security_issues"]:
            st.success("✅ Clean security audit! No critical vulnerabilities or injection vectors detected.")
        else:
            for s in report["security_issues"]:
                sev = s.get("severity", "HIGH")
                badge_class = f"sev-{sev.lower()}"
                border_color = "#F43F5E" if sev == "CRITICAL" else ("#F97316" if sev == "HIGH" else "#EAB308")
                line_badge = ""
                if s.get("line"):
                    line_badge = f"<span class='pill-tag' style='background:rgba(255,255,255,0.08); color:#CBD5E1; font-size:0.8rem; margin-left:8px;'>📍 Line {s['line']}</span>"
                st.markdown(f"""
                <div class="issue-card" style="border-left: 4px solid {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
                            <span style="font-size: 1.15rem; font-weight: 700; color:#F8FAFC;">{s.get('title')}</span>
                            {line_badge}
                        </div>
                        <span class="sev-badge {badge_class}">{sev}</span>
                    </div>
                    <p style="margin: 8px 0; color: #CBD5E1; font-size:0.95rem;">{s.get('description')}</p>
                    {f'<div style="font-size: 0.85rem; color: #94A3B8; margin-bottom:6px;"><strong>CWE Reference:</strong> <code>{s.get("cwe")}</code></div>' if s.get('cwe') else ''}
                    <div style="margin-top: 6px; font-size: 0.92rem; color: #6EE7B7; background:rgba(16,185,129,0.06); padding:6px 10px; border-radius:6px;">
                        <strong>Remediation:</strong> {s.get('recommendation')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Tab 3: Bugs & Logic Flaws
    with tab_bugs:
        st.markdown("### 🐛 Bugs & Runtime Logic Anomalies")
        if not report["bugs"]:
            st.success("✅ No logic flaws or syntax errors detected.")
        else:
            for b in report["bugs"]:
                sev = b.get("severity", "HIGH")
                badge_class = f"sev-{sev.lower()}"
                border_color = "#F43F5E" if sev == "CRITICAL" else ("#F97316" if sev == "HIGH" else ("#EAB308" if sev == "MEDIUM" else "#38BDF8"))
                line_badge = ""
                if b.get("line"):
                    col_info = f", Col {b['column']}" if b.get('column') else ""
                    line_badge = f"<span class='pill-tag' style='background:rgba(255,255,255,0.08); color:#CBD5E1; font-size:0.8rem; margin-left:8px;'>📍 Line {b['line']}{col_info}</span>"
                
                snippet_html = ""
                if b.get("code_snippet"):
                    snippet_html = f"<div style='margin: 8px 0 10px 0; padding: 6px 12px; background: rgba(0,0,0,0.4); border-left: 2px solid {border_color}; border-radius: 4px; font-family: monospace; font-size: 0.88rem; color: #F1F5F9;'><code>{b['code_snippet']}</code></div>"

                st.markdown(f"""
                <div class="issue-card" style="border-left: 4px solid {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
                            <span style="font-size: 1.1rem; font-weight: 700; color:#F8FAFC;">{b.get('title')}</span>
                            {line_badge}
                        </div>
                        <span class="sev-badge {badge_class}">{sev}</span>
                    </div>
                    <p style="margin: 8px 0; color: #CBD5E1; font-size:0.95rem;">{b.get('description')}</p>
                    {snippet_html}
                    <div style="margin-top: 6px; font-size: 0.92rem; color: #93C5FD; background:rgba(59,130,246,0.06); padding:6px 10px; border-radius:6px;">
                        <strong>Resolution:</strong> {b.get('recommendation')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Tab 4: Code Smells & Style
    with tab_smells:
        st.markdown("### 🧹 Architectural & Cognitive Code Smells")
        if not report["code_smells"]:
            st.info("✅ No architectural code smells detected.")
        else:
            for sm in report["code_smells"]:
                st.markdown(f"""
                <div class="issue-card" style="border-left: 4px solid #FDE047;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color:#F8FAFC; font-size:1.05rem;">💡 {sm.get('title')}</span>
                        <span class="sev-badge sev-medium">{sm.get('severity', 'MEDIUM')}</span>
                    </div>
                    <p style="margin: 6px 0; color: #CBD5E1; font-size:0.92rem;">{sm.get('description')}</p>
                    <div style="font-size: 0.88rem; color: #6EE7B7;"><strong>Refactoring Tip:</strong> {sm.get('recommendation')}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("### 🎨 Code Style & Conventions")
        if not report["style_issues"]:
            st.success("✅ Clean code formatting and convention conformance.")
        else:
            for st_issue in report["style_issues"]:
                st.markdown(f"""
                <div style="padding:8px 12px; background:rgba(255,255,255,0.02); border-left:3px solid #38BDF8; margin-bottom:8px; border-radius:4px;">
                    <strong style="color:#38BDF8;">{st_issue.get('rule')}</strong>: <span style="color:#CBD5E1;">{st_issue.get('description')}</span>
                </div>
                """, unsafe_allow_html=True)

    # Tab 5: Auto-Fix & Diff
    with tab_diff:
        st.markdown("### 🔄 Automated Code Fix & Diff Comparison")

        diff_mode = st.radio("Display Format:", ["Side-by-Side Comparison", "Unified Git Diff"], horizontal=True)

        lang_syntax = report["language"].lower()
        if lang_syntax == "mongodb":
            lang_syntax = "javascript"

        if diff_mode == "Side-by-Side Comparison":
            col_orig, col_fixed = st.columns(2)
            with col_orig:
                st.markdown("##### ❌ Original Code (Before)")
                st.code(code_input, language=lang_syntax)
            with col_fixed:
                st.markdown("##### ✅ Auto-Fixed Code (After)")
                st.code(report["suggested_fix"], language=lang_syntax)
        else:
            st.markdown("##### 🔀 Unified Line Diff")
            if report.get("unified_diff"):
                st.code(report["unified_diff"], language="diff")
            else:
                st.info("No line alterations detected.")

        st.markdown("#### 📋 Clean Refactored Snippet")
        st.code(report["suggested_fix"], language=lang_syntax)

    # Tab 6: Unit Tests
    with tab_tests:
        st.markdown(f"### 🧪 Generated Test Suite ({report['language']})")
        st.markdown("Autonomous unit tests covering standard cases, edge bounds, and negative assertions:")
        st.code(report["test_cases"], language=lang_syntax)

    # Tab 7: Best Practices
    with tab_bp:
        st.markdown("### 💡 Senior Engineering Recommendations")
        for bp in report["best_practices"]:
            st.markdown(f"""
            <div style="padding:10px 14px; background:rgba(255,255,255,0.02); border-left:3px solid #818CF8; border-radius:6px; margin-bottom:10px; color:#E2E8F0;">
                {bp}
            </div>
            """, unsafe_allow_html=True)

    # Tab 8: Export Report
    with tab_export:
        st.markdown("### 📥 Download & Export")
        st.download_button(
            label="📄 Download Full Markdown Report (.md)",
            data=report["markdown_report"],
            file_name=f"nexreview_{report['language'].lower()}_report.md",
            mime="text/markdown",
            use_container_width=True
        )
        with st.expander("👁️ Preview Raw Markdown"):
            st.markdown(report["markdown_report"])