/**
 * NexReview AI - Client Application Logic
 */

const STORAGE_KEY = "nexreview_backend_url";
const DEFAULT_RENDER_BACKEND = "https://code-reviewer-agent.onrender.com";

function getInitialBackendUrl() {
  const saved = localStorage.getItem(STORAGE_KEY);
  // If user previously saved localhost while on remote HTTPS, ignore localhost and use Render
  if (saved && (!saved.includes("localhost") || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
    return saved;
  }
  // If running locally on localhost or 127.0.0.1
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return window.location.port === "8000" ? window.location.origin : "http://localhost:8000";
  }
  // Default for Vercel, mobile devices, and all remote environments
  return DEFAULT_RENDER_BACKEND;
}

let currentBackendUrl = getInitialBackendUrl();
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

function initApp() {
  const editor = document.getElementById("code-editor");
  const languageSelect = document.getElementById("language-select");
  const sampleSelect = document.getElementById("sample-select");
  const statsEl = document.getElementById("editor-stats");
  const runBtn = document.getElementById("run-review-btn");
  const clearBtn = document.getElementById("clear-code-btn");
  const resetBtn = document.getElementById("reset-sample-btn");
  const statusPill = document.getElementById("backend-status-pill");
  const configCard = document.getElementById("backend-config-card");
  const closeConfigBtn = document.getElementById("close-config-btn");
  const backendUrlInput = document.getElementById("backend-url-input");
  const testConnBtn = document.getElementById("test-connection-btn");
  const saveConfigBtn = document.getElementById("save-config-btn");
  const connFeedback = document.getElementById("connection-test-feedback");
  const modeSideBtn = document.getElementById("mode-side-btn");
  const modeUnifiedBtn = document.getElementById("mode-unified-btn");
  const diffSideView = document.getElementById("diff-side-view");
  const diffUnifiedView = document.getElementById("diff-unified-view");
  const copyFixBtn = document.getElementById("copy-fix-btn");
  const copyTestsBtn = document.getElementById("copy-tests-btn");
  const downloadReportBtn = document.getElementById("download-report-btn");

  if (!editor) {
    console.warn("NexReview: #code-editor not found during initApp");
    return;
  }

  // Set backend input initial value
  if (backendUrlInput) {
    backendUrlInput.value = currentBackendUrl;
  }

  // Update stats helper
  function updateStats() {
    const text = editor ? editor.value : "";
    const chars = text.length;
    const lines = text ? text.split("\n").length : 0;
    if (statsEl) {
      statsEl.textContent = `${chars} characters • ${lines} lines`;
    }
  }

  // Load sample snippet
  function loadSample(sampleKey) {
    if (sampleSnippets[sampleKey]) {
      const s = sampleSnippets[sampleKey];
      editor.value = s.code;
      if (s.language && languageSelect) {
        languageSelect.value = s.language;
      }
      updateStats();
    }
  }

  // Bind input listeners
  ["input", "keyup", "paste", "change"].forEach((evt) => {
    editor.addEventListener(evt, updateStats);
  });

  // Load initial sample
  if (sampleSelect && sampleSelect.value) {
    loadSample(sampleSelect.value);
  } else {
    loadSample("python_sqli");
  }

  updateStats();

  // Sample select change
  if (sampleSelect) {
    sampleSelect.addEventListener("change", (e) => {
      loadSample(e.target.value);
    });
  }

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      editor.value = "";
      updateStats();
      editor.focus();
    });
  }

  // Reset sample button
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      const key = (sampleSelect && sampleSelect.value) || "python_sqli";
      loadSample(key);
    });
  }

  // Run Review button
  if (runBtn) {
    runBtn.addEventListener("click", handleRunReview);
  }

  // Backend config drawer
  if (statusPill && configCard) {
    statusPill.addEventListener("click", () => {
      configCard.style.display = configCard.style.display === "none" ? "block" : "none";
    });
  }

  if (closeConfigBtn && configCard) {
    closeConfigBtn.addEventListener("click", () => {
      configCard.style.display = "none";
    });
  }

  if (testConnBtn && backendUrlInput && connFeedback) {
    testConnBtn.addEventListener("click", async () => {
      const url = backendUrlInput.value.trim().replace(/\/$/, "");
      connFeedback.textContent = "Testing endpoint...";
      connFeedback.style.color = "#94A3B8";
      const ok = await checkBackendHealth(url);
      if (ok) {
        connFeedback.textContent = "✅ Connected successfully to Render backend!";
        connFeedback.style.color = "#6EE7B7";
      } else {
        connFeedback.textContent = "❌ Failed to connect. Verify your Render service URL & that it's online.";
        connFeedback.style.color = "#FDA4AF";
      }
    });
  }

  if (saveConfigBtn && backendUrlInput && configCard) {
    saveConfigBtn.addEventListener("click", () => {
      const url = backendUrlInput.value.trim().replace(/\/$/, "");
      if (url) {
        currentBackendUrl = url;
        localStorage.setItem(STORAGE_KEY, url);
        checkBackendHealth(url);
        configCard.style.display = "none";
      }
    });
  }

  // Diff toggles
  if (modeSideBtn && modeUnifiedBtn && diffSideView && diffUnifiedView) {
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
  }

  // Copy buttons
  if (copyFixBtn) {
    copyFixBtn.addEventListener("click", () => {
      if (currentReport && currentReport.suggested_fix) {
        navigator.clipboard.writeText(currentReport.suggested_fix);
        copyFixBtn.textContent = "✅ Copied!";
        setTimeout(() => { copyFixBtn.textContent = "📋 Copy Fix"; }, 2000);
      }
    });
  }

  if (copyTestsBtn) {
    copyTestsBtn.addEventListener("click", () => {
      if (currentReport && currentReport.test_cases) {
        navigator.clipboard.writeText(currentReport.test_cases);
        copyTestsBtn.textContent = "✅ Copied!";
        setTimeout(() => { copyTestsBtn.textContent = "📋 Copy Tests"; }, 2000);
      }
    });
  }

  if (downloadReportBtn) {
    downloadReportBtn.addEventListener("click", handleDownloadReport);
  }

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

  // Check health
  checkBackendHealth(currentBackendUrl);
}

// Auto run when script loads or on DOMContentLoaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}

async function checkBackendHealth(url) {
  let targetUrl = (url || "").trim().replace(/\/+$/, "");

  // Auto-upgrade to Render HTTPS if on remote HTTPS
  if (window.location.protocol === "https:" && targetUrl.startsWith("http://")) {
    targetUrl = DEFAULT_RENDER_BACKEND;
    currentBackendUrl = DEFAULT_RENDER_BACKEND;
    localStorage.setItem(STORAGE_KEY, DEFAULT_RENDER_BACKEND);
    const backendUrlInput = document.getElementById("backend-url-input");
    if (backendUrlInput) backendUrlInput.value = DEFAULT_RENDER_BACKEND;
  }

  const backendIndicator = document.getElementById("backend-indicator");
  const backendStatusText = document.getElementById("backend-status-text");

  if (backendIndicator) backendIndicator.className = "pulse-dot pulse-amber";
  if (backendStatusText) backendStatusText.textContent = "Backend: Connecting...";

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const res = await fetch(`${targetUrl}/api/health`, { 
      method: "GET",
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      if (backendIndicator) backendIndicator.className = "pulse-dot";
      if (backendStatusText) backendStatusText.textContent = "Backend: Online";

      // Load languages & samples dynamically
      fetch(`${targetUrl}/api/samples`)
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
      if (backendIndicator) backendIndicator.className = "pulse-dot pulse-red";
      if (backendStatusText) backendStatusText.textContent = "Backend: Error";
      return false;
    }
  } catch (e) {
    if (backendIndicator) backendIndicator.className = "pulse-dot pulse-amber";
    if (backendStatusText) backendStatusText.textContent = "Backend: Waking up Render...";
    // Automatically retry in 4 seconds while Render cold start finishes
    setTimeout(() => {
      checkBackendHealth(targetUrl);
    }, 4000);
    return false;
  }
}

function populateSampleSelect(samplesObj) {
  const sampleSelect = document.getElementById("sample-select");
  if (!sampleSelect) return;
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
  const editor = document.getElementById("code-editor");
  const languageSelect = document.getElementById("language-select");
  const loadingContainer = document.getElementById("loading-container");
  const runBtn = document.getElementById("run-review-btn");
  const reportSection = document.getElementById("report-section");

  const code = editor ? editor.value.trim() : "";
  if (!code) {
    showError("Please paste or write source code before initiating review.");
    return;
  }

  // Ensure clean HTTPS backend URL on remote HTTPS environments
  let targetUrl = (currentBackendUrl || DEFAULT_RENDER_BACKEND).trim().replace(/\/+$/, "");
  if (window.location.protocol === "https:" && targetUrl.startsWith("http://")) {
    targetUrl = DEFAULT_RENDER_BACKEND;
    currentBackendUrl = DEFAULT_RENDER_BACKEND;
    localStorage.setItem(STORAGE_KEY, DEFAULT_RENDER_BACKEND);
  }

  hideError();
  if (loadingContainer) loadingContainer.style.display = "flex";
  if (runBtn) {
    runBtn.disabled = true;
    const btnText = runBtn.querySelector(".btn-text");
    if (btnText) btnText.textContent = "Analyzing Code...";
  }
  currentCode = code;

  try {
    const res = await fetch(`${targetUrl}/api/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: code,
        language: (languageSelect && languageSelect.value) || "Auto-Detect"
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (Status ${res.status})`);
    }

    const report = await res.json();
    currentReport = report;
    renderReport(report);
    if (reportSection) {
      reportSection.style.display = "block";
      reportSection.scrollIntoView({ behavior: "smooth" });
    }
  } catch (err) {
    showError(`Review request failed: ${err.message}. Ensure your Render backend service is running and accessible at: ${currentBackendUrl} (Click the ⚙️ icon at the top right to change).`);
  } finally {
    if (loadingContainer) loadingContainer.style.display = "none";
    if (runBtn) {
      runBtn.disabled = false;
      const btnText = runBtn.querySelector(".btn-text");
      if (btnText) btnText.textContent = "Run Comprehensive Review";
    }
  }
}

function showError(msg) {
  const errorBanner = document.getElementById("error-banner");
  if (errorBanner) {
    errorBanner.textContent = `⚠️ ${msg}`;
    errorBanner.style.display = "block";
    errorBanner.scrollIntoView({ behavior: "smooth" });
  } else {
    alert(msg);
  }
}

function hideError() {
  const errorBanner = document.getElementById("error-banner");
  if (errorBanner) {
    errorBanner.style.display = "none";
  }
}

function renderReport(report) {
  const criticalAlert = document.getElementById("critical-alert");
  const scoreValue = document.getElementById("score-value");
  const scoreBadgeWrap = document.getElementById("score-badge-wrap");
  const reportLangMain = document.getElementById("report-lang-main");
  const reportLangSub = document.getElementById("report-lang-sub");
  const reportTimeComp = document.getElementById("report-time-comp");
  const reportSpaceComp = document.getElementById("report-space-comp");

  const subSecVal = document.getElementById("sub-sec-val");
  const subSecBar = document.getElementById("sub-sec-bar");
  const subMaintVal = document.getElementById("sub-maint-val");
  const subMaintBar = document.getElementById("sub-maint-bar");
  const subPerfVal = document.getElementById("sub-perf-val");
  const subPerfBar = document.getElementById("sub-perf-bar");

  const chipCritical = document.getElementById("chip-critical");
  const chipHigh = document.getElementById("chip-high");
  const chipMedium = document.getElementById("chip-medium");
  const chipLow = document.getElementById("chip-low");

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

  const testsCode = document.getElementById("tests-code");
  const practicesList = document.getElementById("practices-list");
  const markdownPreview = document.getElementById("markdown-preview");

  // 1. Critical Alert
  const hasCritical = report.has_fatal_syntax || (report.severity_counts && report.severity_counts.CRITICAL > 0);
  if (criticalAlert) criticalAlert.style.display = hasCritical ? "flex" : "none";

  // 2. Metrics Header
  const score = report.quality_score || 0;
  if (scoreValue) {
    scoreValue.innerHTML = `${score}<span class="score-den">/100</span>`;
    scoreValue.className = "score-glow " + (score >= 85 ? "score-excellent" : score >= 60 ? "score-warning" : "score-danger");
  }

  if (scoreBadgeWrap) {
    scoreBadgeWrap.innerHTML = score >= 85
      ? '<span class="sev-badge" style="background:rgba(16,185,129,0.2); color:#6EE7B7; border:1px solid #10B981;">🟢 Production Ready</span>'
      : score >= 60
      ? '<span class="sev-badge" style="background:rgba(245,158,11,0.2); color:#FDE047; border:1px solid #F59E0B;">🟡 Needs Remediation</span>'
      : '<span class="sev-badge" style="background:rgba(244,63,94,0.2); color:#FDA4AF; border:1px solid #F43F5E;">🔴 Critical Risk</span>';
  }

  if (reportLangMain) reportLangMain.textContent = report.language || "Unknown";
  if (reportLangSub) reportLangSub.textContent = report.language_display || report.language || "";
  if (reportTimeComp) reportTimeComp.textContent = report.time_complexity || "O(N)";
  if (reportSpaceComp) reportSpaceComp.textContent = report.space_complexity || "O(1)";

  // 3. Sub-scores
  if (report.sub_scores) {
    const { security = 0, maintainability = 0, performance = 0 } = report.sub_scores;
    if (subSecVal) subSecVal.textContent = `${security}/100`;
    if (subSecBar) subSecBar.style.width = `${security}%`;

    if (subMaintVal) subMaintVal.textContent = `${maintainability}/100`;
    if (subMaintBar) subMaintBar.style.width = `${maintainability}%`;

    if (subPerfVal) subPerfVal.textContent = `${performance}/100`;
    if (subPerfBar) subPerfBar.style.width = `${performance}%`;
  }

  // 4. Severity Counts
  if (report.severity_counts) {
    if (chipCritical) chipCritical.textContent = `🚨 Critical (${report.severity_counts.CRITICAL || 0})`;
    if (chipHigh) chipHigh.textContent = `⚠️ High Priority (${report.severity_counts.HIGH || 0})`;
    if (chipMedium) chipMedium.textContent = `💡 Medium (${report.severity_counts.MEDIUM || 0})`;
    if (chipLow) chipLow.textContent = `ℹ️ Style / Low (${report.severity_counts.LOW || 0})`;
  }

  // 5. Tabs Counters
  const secIssues = report.security_issues || [];
  const bugIssues = report.bugs || [];
  const smellIssues = report.code_smells || [];
  const styleIssues = report.style_issues || [];

  if (countSec) countSec.textContent = secIssues.length;
  if (countBugs) countBugs.textContent = bugIssues.length;
  if (countSmells) countSmells.textContent = smellIssues.length + styleIssues.length;

  // 6. Tab 1: Executive Summary & Complexity
  if (execSummaryBox) execSummaryBox.textContent = report.executive_summary || "No executive summary available.";
  if (detailTimeComp) detailTimeComp.textContent = report.time_complexity || "O(N)";
  if (detailSpaceComp) detailSpaceComp.textContent = report.space_complexity || "O(1)";
  if (complexityExplanation) {
    complexityExplanation.innerHTML = report.complexity_explanation ? `<strong>Detailed Complexity Rationale:</strong><p style="margin-top:4px;">${escapeHtml(report.complexity_explanation)}</p>` : "";
  }

  // 7. Tab 2: Security Vulnerabilities
  if (securityIssuesList) {
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
  }

  // 8. Tab 3: Bugs
  if (bugsList) {
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
  }

  // 9. Tab 4: Code Smells & Style
  if (smellsList) {
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
  }

  if (styleList) {
    if (styleIssues.length === 0) {
      styleList.innerHTML = '<div style="padding:12px; background:rgba(255,255,255,0.02); border-radius:8px; color:#94A3B8;">✅ Clean code formatting and convention conformance.</div>';
    } else {
      styleList.innerHTML = styleIssues.map((st) => `
        <div style="padding:8px 12px; background:rgba(255,255,255,0.02); border-left:3px solid #38BDF8; margin-bottom:8px; border-radius:4px; font-size:0.88rem;">
          <strong style="color:#38BDF8;">${escapeHtml(st.rule || "Style")}:</strong> <span style="color:#CBD5E1;">${escapeHtml(st.description || "")}</span>
        </div>
      `).join("");
    }
  }

  // 10. Tab 5: Auto-Fix & Diff
  if (diffOrigCode) diffOrigCode.textContent = currentCode;
  if (diffFixedCode) diffFixedCode.textContent = report.suggested_fix || currentCode;
  if (diffUnifiedCode) diffUnifiedCode.textContent = report.unified_diff || "No line alterations detected.";

  // 11. Tab 6: Unit Tests
  if (testsCode) testsCode.textContent = report.test_cases || "// No test cases generated.";

  // 12. Tab 7: Best Practices
  if (practicesList) {
    const practices = report.best_practices || [];
    if (practices.length === 0) {
      practicesList.innerHTML = '<p style="color:#94A3B8;">No special recommendations for this snippet.</p>';
    } else {
      practicesList.innerHTML = practices.map((bp) => `
        <div class="practice-item">${escapeHtml(bp)}</div>
      `).join("");
    }
  }

  // 13. Tab 8: Export
  if (markdownPreview) markdownPreview.textContent = report.markdown_report || "";
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
