/**
 * NexReview AI - Client Application Logic
 */

// Default backend: uses deployed origin or saved in localStorage or localhost:8000
const STORAGE_KEY = "nexreview_backend_url";
let currentBackendUrl = localStorage.getItem(STORAGE_KEY) || (window.location.port === "8000" ? window.location.origin : "http://localhost:8000");

let currentReport = null;
let currentCode = "";

const FALLBACK_SAMPLES = {
  python_sqli: {
    title: "🐍 Python: Dynamic SQL Injection",
    language: "Python",
    code: `import sqlite3\n\ndef fetch_user_record(username):\n    conn = sqlite3.connect("app.db")\n    cursor = conn.cursor()\n    # High Risk: Dynamic f-string allows SQL injection\n    query = f"SELECT id, username, email FROM users WHERE name = '{username}'"\n    cursor.execute(query)\n    return cursor.fetchall()`
  },
  sql_cartesian: {
    title: "🗄️ SQL: Unindexed Cartesian Join & DELETE",
    language: "SQL",
    code: `-- Critical: Unconditional DELETE + Wildcard Join\nDELETE FROM audit_logs;\n\nSELECT * \nFROM users u, transactions t, accounts a\nWHERE u.status = 'active'\nORDER BY t.created_at DESC;`
  },
  mongo_injection: {
    title: "🍃 MongoDB: NoSQL $where Injection",
    language: "MongoDB",
    code: `// NoSQL Injection via $where + Unbounded Query\nconst targetName = req.body.username;\n\ndb.users.find({\n    $where: "this.username == '" + targetName + "'"\n});\n\n// Dangerous unbounded fetch\nconst allRecords = db.audit_trails.find({});`
  },
  perl_open: {
    title: "🐪 Perl: Two-Argument open() Vulnerability",
    language: "Perl",
    code: `#!/usr/bin/perl\n# Insecure 2-arg open() permits pipe command injection\n\nsub read_user_file {\n    my ($file) = @_;\n    \n    # Bug: 2-arg open allows "| rm -rf /" shell execution\n    open(FILE, "< $file") or die "Cannot open: $!";\n    \n    while (<FILE>) {\n        print $_;\n    }\n    close(FILE);\n}\n\nread_user_file("data.txt");`
  },
  php_scope: {
    title: "🐘 PHP: Zero Division & Broken Scope",
    language: "PHP",
    code: `<?php\n$numbers = [10, 20, 30, 40, 50];\n\nfor ($i = 0; $i < count($numbers); $i++) {\n    $total += $numbers[$i];\n}\n\n$average = $total / 0;\n\necho "Average: " . calculateAverage($numbers);\n?>`
  },
  js_xss: {
    title: "⚡ JavaScript: DOM XSS & Loose Coercion",
    language: "JavaScript",
    code: `// DOM XSS via innerHTML and loose equality\nfunction renderUserProfile(userData) {\n    const userRole = userData.role;\n    \n    // Loose equality hazard\n    if (userRole == "admin") {\n        document.getElementById("badge").innerHTML = "<b>" + userData.name + "</b>";\n    }\n    \n    let total = 0;\n    let avg = total / 0;\n    console.log("Average:", avg);\n}`
  },
  c_overflow: {
    title: "⚙️ C: Unbounded Buffer Overflow",
    language: "C",
    code: `#include <stdio.h>\n#include <string.h>\n\nvoid execute_task(char *input_str) {\n    char local_buf[16];\n    // Dangerous: gets and strcpy lack bounds checking\n    strcpy(local_buf, input_str);\n    printf("Result: %s\\n", local_buf);\n}\n\nint main() {\n    execute_task("This string exceeds sixteen bytes limit!");\n    return 0;\n}`
  },
  java_resource: {
    title: "☕ Java: Resource Leak & Concatenation",
    language: "Java",
    code: `import java.io.*;\n\npublic class FileParser {\n    public void dumpFile(String path) throws IOException {\n        // Resource leak: unclosed stream without try-with-resources\n        BufferedReader reader = new BufferedReader(new FileReader(path));\n        String line = reader.readLine();\n        System.out.println("First line: " + line);\n    }\n}`
  }
};

let sampleSnippets = FALLBACK_SAMPLES;

// DOM Elements
const editor = document.getElementById("code-editor");
const languageSelect = document.getElementById("language-select");
const sampleSelect = document.getElementById("sample-select");
const statsEl = document.getElementById("editor-stats");
const runBtn = document.getElementById("run-review-btn");
const clearBtn = document.getElementById("clear-code-btn");
const resetBtn = document.getElementById("reset-sample-btn");
const loadingContainer = document.getElementById("loading-container");
const errorBanner = document.getElementById("error-banner");
const reportSection = document.getElementById("report-section");

// Header status
const statusPill = document.getElementById("backend-status-pill");
const backendIndicator = document.getElementById("backend-indicator");
const backendStatusText = document.getElementById("backend-status-text");

// Config drawer
const configCard = document.getElementById("backend-config-card");
const closeConfigBtn = document.getElementById("close-config-btn");
const backendUrlInput = document.getElementById("backend-url-input");
const testConnBtn = document.getElementById("test-connection-btn");
const saveConfigBtn = document.getElementById("save-config-btn");
const connFeedback = document.getElementById("connection-test-feedback");

// Report elements
const criticalAlert = document.getElementById("critical-alert");
const scoreValue = document.getElementById("score-value");
const scoreBadgeWrap = document.getElementById("score-badge-wrap");
const reportLangMain = document.getElementById("report-lang-main");
const reportLangSub = document.getElementById("report-lang-sub");
const reportTimeComp = document.getElementById("report-time-comp");
const reportSpaceComp = document.getElementById("report-space-comp");

// Sub scores
const subSecVal = document.getElementById("sub-sec-val");
const subSecBar = document.getElementById("sub-sec-bar");
const subMaintVal = document.getElementById("sub-maint-val");
const subMaintBar = document.getElementById("sub-maint-bar");
const subPerfVal = document.getElementById("sub-perf-val");
const subPerfBar = document.getElementById("sub-perf-bar");

// Severity chips
const chipCritical = document.getElementById("chip-critical");
const chipHigh = document.getElementById("chip-high");
const chipMedium = document.getElementById("chip-medium");
const chipLow = document.getElementById("chip-low");

// Tabs
const countSec = document.getElementById("count-sec");
const countBugs = document.getElementById("count-bugs");
const countSmells = document.getElementById("count-smells");

const execSummaryBox = document.getElementById("exec-summary-box");
const detailTimeComp = document.getElementById("detail-time-comp");
const detailSpaceComp = document.getElementById("detail-space-comp");
const complexityExplanation = document.getElementById("complexity-explanation");

const securityIssuesList = document.getElementById("security-issues-list");
const bugsList = document.getElementById("bugs-list");
const smellsList = document.getElementById("smells-list");
const styleList = document.getElementById("style-list");

const diffOrigCode = document.getElementById("diff-orig-code");
const diffFixedCode = document.getElementById("diff-fixed-code");
const diffUnifiedCode = document.getElementById("diff-unified-code");
const modeSideBtn = document.getElementById("mode-side-btn");
const modeUnifiedBtn = document.getElementById("mode-unified-btn");
const diffSideView = document.getElementById("diff-side-view");
const diffUnifiedView = document.getElementById("diff-unified-view");
const copyFixBtn = document.getElementById("copy-fix-btn");

const testsCode = document.getElementById("tests-code");
const copyTestsBtn = document.getElementById("copy-tests-btn");
const practicesList = document.getElementById("practices-list");
const downloadReportBtn = document.getElementById("download-report-btn");
const markdownPreview = document.getElementById("markdown-preview");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  backendUrlInput.value = currentBackendUrl;
  updateStats();
  loadInitialSample("python_sqli");
  checkBackendHealth(currentBackendUrl);

  // Editor stats
  editor.addEventListener("input", updateStats);

  // Sample select change
  sampleSelect.addEventListener("change", (e) => {
    loadInitialSample(e.target.value);
  });

  // Action buttons
  clearBtn.addEventListener("click", () => {
    editor.value = "";
    updateStats();
  });

  resetBtn.addEventListener("click", () => {
    loadInitialSample(sampleSelect.value || "python_sqli");
  });

  runBtn.addEventListener("click", handleRunReview);

  // Backend config drawer
  statusPill.addEventListener("click", () => {
    configCard.style.display = configCard.style.display === "none" ? "block" : "none";
  });

  closeConfigBtn.addEventListener("click", () => {
    configCard.style.display = "none";
  });

  testConnBtn.addEventListener("click", async () => {
    const url = backendUrlInput.value.trim().replace(/\/$/, "");
    connFeedback.textContent = "Testing endpoint...";
    connFeedback.style.color = "#94A3B8";
    const ok = await checkBackendHealth(url);
    if (ok) {
      connFeedback.textContent = "✅ Connected successfully to Render backend!";
      connFeedback.style.color = "#6EE7B7";
    } else {
      connFeedback.textContent = "❌ Failed to connect. Verify your Render service URL.";
      connFeedback.style.color = "#FDA4AF";
    }
  });

  saveConfigBtn.addEventListener("click", () => {
    const url = backendUrlInput.value.trim().replace(/\/$/, "");
    if (url) {
      currentBackendUrl = url;
      localStorage.setItem(STORAGE_KEY, url);
      checkBackendHealth(url);
      configCard.style.display = "none";
    }
  });

  // Diff format toggle
  modeSideBtn.addEventListener("click", () => {
    modeSideBtn.classList.add("active");
    modeUnifiedBtn.classList.remove("active");
    diffSideView.style.display = "grid";
    diffUnifiedView.style.display = "none";
  });

  modeUnifiedBtn.addEventListener("click", () => {
    modeUnifiedBtn.classList.add("active");
    modeSideBtn.classList.remove("active");
    diffSideView.style.display = "none";
    diffUnifiedView.style.display = "block";
  });

  // Copy buttons
  copyFixBtn.addEventListener("click", () => {
    if (currentReport && currentReport.suggested_fix) {
      navigator.clipboard.writeText(currentReport.suggested_fix);
      copyFixBtn.textContent = "✅ Copied!";
      setTimeout(() => { copyFixBtn.textContent = "📋 Copy Fix"; }, 2000);
    }
  });

  copyTestsBtn.addEventListener("click", () => {
    if (currentReport && currentReport.test_cases) {
      navigator.clipboard.writeText(currentReport.test_cases);
      copyTestsBtn.textContent = "✅ Copied!";
      setTimeout(() => { copyTestsBtn.textContent = "📋 Copy Tests"; }, 2000);
    }
  });

  downloadReportBtn.addEventListener("click", handleDownloadReport);

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add("active");
    });
  });
});

function updateStats() {
  const text = editor.value;
  const chars = text.length;
  const lines = text ? text.split("\n").length : 0;
  statsEl.textContent = `${chars} characters • ${lines} lines`;
}

function loadInitialSample(sampleKey) {
  if (sampleSnippets[sampleKey]) {
    const s = sampleSnippets[sampleKey];
    editor.value = s.code;
    if (s.language) {
      languageSelect.value = s.language;
    }
    updateStats();
  }
}

async function checkBackendHealth(url) {
  backendIndicator.className = "pulse-dot pulse-amber";
  backendStatusText.textContent = "Backend: Connecting...";

  try {
    const res = await fetch(`${url}/api/health`, { method: "GET" });
    if (res.ok) {
      backendIndicator.className = "pulse-dot";
      backendStatusText.textContent = "Backend: Online";

      // Load languages & samples dynamically
      fetch(`${url}/api/samples`)
        .then((r) => r.json())
        .then((data) => {
          if (data.samples) {
            sampleSnippets = data.samples;
            populateSampleSelect(data.samples);
          }
        })
        .catch(() => {});

      return true;
    } else {
      backendIndicator.className = "pulse-dot pulse-red";
      backendStatusText.textContent = "Backend: Error";
      return false;
    }
  } catch (e) {
    backendIndicator.className = "pulse-dot pulse-red";
    backendStatusText.textContent = "Backend: Offline";
    return false;
  }
}

function populateSampleSelect(samplesObj) {
  const currentVal = sampleSelect.value;
  sampleSelect.innerHTML = '<option value="">-- Choose Sample Snippet --</option>';
  for (const [key, item] of Object.entries(samplesObj)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = item.title;
    if (key === currentVal) opt.selected = true;
    sampleSelect.appendChild(opt);
  }
}

async function handleRunReview() {
  const code = editor.value.trim();
  if (!code) {
    showError("Please paste or write source code before initiating review.");
    return;
  }

  hideError();
  loadingContainer.style.display = "flex";
  runBtn.disabled = true;
  runBtn.querySelector(".btn-text").textContent = "Analyzing Code...";
  currentCode = code;

  try {
    const res = await fetch(`${currentBackendUrl}/api/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: code,
        language: languageSelect.value || "Auto-Detect"
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (Status ${res.status})`);
    }

    const report = await res.json();
    currentReport = report;
    renderReport(report);
    reportSection.style.display = "block";
    reportSection.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showError(`Review failed: ${err.message}. Make sure your Render backend is running at ${currentBackendUrl}`);
  } finally {
    loadingContainer.style.display = "none";
    runBtn.disabled = false;
    runBtn.querySelector(".btn-text").textContent = "Run Comprehensive Review";
  }
}

function showError(msg) {
  errorBanner.textContent = `⚠️ ${msg}`;
  errorBanner.style.display = "block";
}

function hideError() {
  errorBanner.style.display = "none";
}

function renderReport(report) {
  // 1. Critical Alert
  const hasCritical = report.has_fatal_syntax || (report.severity_counts && report.severity_counts.CRITICAL > 0);
  criticalAlert.style.display = hasCritical ? "flex" : "none";

  // 2. Metrics Header
  const score = report.quality_score || 0;
  scoreValue.innerHTML = `${score}<span class="score-den">/100</span>`;
  scoreValue.className = "score-glow " + (score >= 85 ? "score-excellent" : score >= 60 ? "score-warning" : "score-danger");

  scoreBadgeWrap.innerHTML = score >= 85
    ? '<span class="sev-badge" style="background:rgba(16,185,129,0.2); color:#6EE7B7; border:1px solid #10B981;">🟢 Production Ready</span>'
    : score >= 60
    ? '<span class="sev-badge" style="background:rgba(245,158,11,0.2); color:#FDE047; border:1px solid #F59E0B;">🟡 Needs Remediation</span>'
    : '<span class="sev-badge" style="background:rgba(244,63,94,0.2); color:#FDA4AF; border:1px solid #F43F5E;">🔴 Critical Risk</span>';

  reportLangMain.textContent = report.language || "Unknown";
  reportLangSub.textContent = report.language_display || report.language || "";
  reportTimeComp.textContent = report.time_complexity || "O(N)";
  reportSpaceComp.textContent = report.space_complexity || "O(1)";

  // 3. Sub-scores
  if (report.sub_scores) {
    const { security = 0, maintainability = 0, performance = 0 } = report.sub_scores;
    subSecVal.textContent = `${security}/100`;
    subSecBar.style.width = `${security}%`;

    subMaintVal.textContent = `${maintainability}/100`;
    subMaintBar.style.width = `${maintainability}%`;

    subPerfVal.textContent = `${performance}/100`;
    subPerfBar.style.width = `${performance}%`;
  }

  // 4. Severity Counts
  if (report.severity_counts) {
    chipCritical.textContent = `🚨 Critical (${report.severity_counts.CRITICAL || 0})`;
    chipHigh.textContent = `⚠️ High Priority (${report.severity_counts.HIGH || 0})`;
    chipMedium.textContent = `💡 Medium (${report.severity_counts.MEDIUM || 0})`;
    chipLow.textContent = `ℹ️ Style / Low (${report.severity_counts.LOW || 0})`;
  }

  // 5. Tabs Counters
  const secIssues = report.security_issues || [];
  const bugIssues = report.bugs || [];
  const smellIssues = report.code_smells || [];
  const styleIssues = report.style_issues || [];

  countSec.textContent = secIssues.length;
  countBugs.textContent = bugIssues.length;
  countSmells.textContent = smellIssues.length + styleIssues.length;

  // 6. Tab 1: Executive Summary & Complexity
  execSummaryBox.textContent = report.executive_summary || "No executive summary available.";
  detailTimeComp.textContent = report.time_complexity || "O(N)";
  detailSpaceComp.textContent = report.space_complexity || "O(1)";
  complexityExplanation.innerHTML = report.complexity_explanation ? `<strong>Detailed Complexity Rationale:</strong><p style="margin-top:4px;">${escapeHtml(report.complexity_explanation)}</p>` : "";

  // 7. Tab 2: Security Vulnerabilities
  if (secIssues.length === 0) {
    securityIssuesList.innerHTML = '<div style="padding:14px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; color:#6EE7B7;">✅ Clean security audit! No vulnerabilities detected.</div>';
  } else {
    securityIssuesList.innerHTML = secIssues.map((issue) => `
      <div class="issue-card" style="border-left: 4px solid ${getSevColor(issue.severity)};">
        <div class="issue-header">
          <div class="issue-title-wrap">
            <span class="issue-title">${escapeHtml(issue.title || "Vulnerability")}</span>
            ${issue.line ? `<span class="line-tag">📍 Line ${issue.line}</span>` : ""}
          </div>
          ${getBadgeHtml(issue.severity)}
        </div>
        <p class="issue-desc">${escapeHtml(issue.description || "")}</p>
        ${issue.cwe ? `<div class="cwe-ref"><strong>CWE Reference:</strong> <code>${escapeHtml(issue.cwe)}</code></div>` : ""}
        <div class="issue-remediation"><strong>Remediation:</strong> ${escapeHtml(issue.recommendation || "")}</div>
      </div>
    `).join("");
  }

  // 8. Tab 3: Bugs
  if (bugIssues.length === 0) {
    bugsList.innerHTML = '<div style="padding:14px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; color:#6EE7B7;">✅ No logic flaws or syntax errors detected.</div>';
  } else {
    bugsList.innerHTML = bugIssues.map((bug) => `
      <div class="issue-card" style="border-left: 4px solid ${getSevColor(bug.severity)};">
        <div class="issue-header">
          <div class="issue-title-wrap">
            <span class="issue-title">${escapeHtml(bug.title || "Bug")}</span>
            ${bug.line ? `<span class="line-tag">📍 Line ${bug.line}${bug.column ? `, Col ${bug.column}` : ""}</span>` : ""}
          </div>
          ${getBadgeHtml(bug.severity)}
        </div>
        <p class="issue-desc">${escapeHtml(bug.description || "")}</p>
        ${bug.code_snippet ? `<pre class="code-pre" style="margin: 8px 0; border-left: 2px solid ${getSevColor(bug.severity)};"><code>${escapeHtml(bug.code_snippet)}</code></pre>` : ""}
        <div class="issue-resolution"><strong>Resolution:</strong> ${escapeHtml(bug.recommendation || "")}</div>
      </div>
    `).join("");
  }

  // 9. Tab 4: Code Smells & Style
  if (smellIssues.length === 0) {
    smellsList.innerHTML = '<div style="padding:12px; background:rgba(255,255,255,0.02); border-radius:8px; color:#94A3B8;">✅ No architectural code smells detected.</div>';
  } else {
    smellsList.innerHTML = smellIssues.map((sm) => `
      <div class="issue-card" style="border-left: 4px solid #FDE047;">
        <div class="issue-header">
          <span style="font-weight:700; color:#F8FAFC;">💡 ${escapeHtml(sm.title || "Code Smell")}</span>
          ${getBadgeHtml(sm.severity || "MEDIUM")}
        </div>
        <p class="issue-desc">${escapeHtml(sm.description || "")}</p>
        <div style="font-size:0.85rem; color:#6EE7B7;"><strong>Refactoring Tip:</strong> ${escapeHtml(sm.recommendation || "")}</div>
      </div>
    `).join("");
  }

  if (styleIssues.length === 0) {
    styleList.innerHTML = '<div style="padding:12px; background:rgba(255,255,255,0.02); border-radius:8px; color:#94A3B8;">✅ Clean code formatting and convention conformance.</div>';
  } else {
    styleList.innerHTML = styleIssues.map((st) => `
      <div style="padding:8px 12px; background:rgba(255,255,255,0.02); border-left:3px solid #38BDF8; margin-bottom:8px; border-radius:4px; font-size:0.88rem;">
        <strong style="color:#38BDF8;">${escapeHtml(st.rule || "Style")}:</strong> <span style="color:#CBD5E1;">${escapeHtml(st.description || "")}</span>
      </div>
    `).join("");
  }

  // 10. Tab 5: Auto-Fix & Diff
  diffOrigCode.textContent = currentCode;
  diffFixedCode.textContent = report.suggested_fix || currentCode;
  diffUnifiedCode.textContent = report.unified_diff || "No line alterations detected.";

  // 11. Tab 6: Unit Tests
  testsCode.textContent = report.test_cases || "// No test cases generated.";

  // 12. Tab 7: Best Practices
  const practices = report.best_practices || [];
  if (practices.length === 0) {
    practicesList.innerHTML = '<p style="color:#94A3B8;">No special recommendations for this snippet.</p>';
  } else {
    practicesList.innerHTML = practices.map((bp) => `
      <div class="practice-item">${escapeHtml(bp)}</div>
    `).join("");
  }

  // 13. Tab 8: Export
  markdownPreview.textContent = report.markdown_report || "";
}

function handleDownloadReport() {
  if (!currentReport || !currentReport.markdown_report) return;
  const blob = new Blob([currentReport.markdown_report], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `nexreview_${(currentReport.language || "analysis").toLowerCase()}_report.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function getSevColor(sev) {
  const s = (sev || "MEDIUM").toUpperCase();
  if (s === "CRITICAL") return "#F43F5E";
  if (s === "HIGH") return "#F97316";
  if (s === "MEDIUM") return "#EAB308";
  return "#38BDF8";
}

function getBadgeHtml(sev) {
  const s = (sev || "MEDIUM").toUpperCase();
  if (s === "CRITICAL") return '<span class="sev-badge sev-critical">🚨 Critical</span>';
  if (s === "HIGH") return '<span class="sev-badge sev-high">⚠️ High</span>';
  if (s === "MEDIUM") return '<span class="sev-badge sev-medium">💡 Medium</span>';
  return '<span class="sev-badge sev-low">ℹ️ Low / Style</span>';
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
