import React, { useState, useEffect } from 'react';

const DEFAULT_BACKEND = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const PRESET_LANGUAGES = [
  "Auto-Detect", "Python", "JavaScript", "TypeScript", "SQL",
  "MongoDB", "Perl", "PHP", "Java", "C", "C++", "C#", "Go",
  "Rust", "Ruby", "HTML/CSS"
];

const FALLBACK_SAMPLES = {
  "sql_cartesian": {
    "title": "🗄️ SQL: Unindexed Cartesian Join & DELETE",
    "language": "SQL",
    "code": `-- Critical: Unconditional DELETE + Wildcard Join\nDELETE FROM audit_logs;\n\nSELECT * \nFROM users u, transactions t, accounts a\nWHERE u.status = 'active'\nORDER BY t.created_at DESC;`
  },
  "mongo_injection": {
    "title": "🍃 MongoDB: NoSQL $where Injection",
    "language": "MongoDB",
    "code": `// NoSQL Injection via $where + Unbounded Query\nconst targetName = req.body.username;\n\ndb.users.find({\n    $where: "this.username == '" + targetName + "'"\n});\n\n// Dangerous unbounded fetch\nconst allRecords = db.audit_trails.find({});`
  },
  "perl_open": {
    "title": "🐪 Perl: Two-Argument open() Vulnerability",
    "language": "Perl",
    "code": `#!/usr/bin/perl\n# Insecure 2-arg open() permits pipe command injection\n\nsub read_user_file {\n    my ($file) = @_;\n    \n    # Bug: 2-arg open allows "| rm -rf /" shell execution\n    open(FILE, "< $file") or die "Cannot open: $!";\n    \n    while (<FILE>) {\n        print $_;\n    }\n    close(FILE);\n}\n\nread_user_file("data.txt");`
  },
  "php_scope": {
    "title": "🐘 PHP: Zero Division & Broken Scope",
    "language": "PHP",
    "code": `<?php\n$numbers = [10, 20, 30, 40, 50];\n\nfor ($i = 0; $i < count($numbers); $i++) {\n    $total += $numbers[$i];\n}\n\n$average = $total / 0;\n\necho "Average: " . calculateAverage($numbers);\n?>`
  },
  "js_xss": {
    "title": "⚡ JavaScript: DOM XSS & Loose Coercion",
    "language": "JavaScript",
    "code": `// DOM XSS via innerHTML and loose equality\nfunction renderUserProfile(userData) {\n    const userRole = userData.role;\n    \n    // Loose equality hazard\n    if (userRole == "admin") {\n        document.getElementById("badge").innerHTML = "<b>" + userData.name + "</b>";\n    }\n    \n    let total = 0;\n    let avg = total / 0;\n    console.log("Average:", avg);\n}`
  },
  "python_sqli": {
    "title": "🐍 Python: Dynamic SQL Injection",
    "language": "Python",
    "code": `import sqlite3\n\ndef fetch_user_record(username):\n    conn = sqlite3.connect("app.db")\n    cursor = conn.cursor()\n    # High Risk: Dynamic f-string allows SQL injection\n    query = f"SELECT id, username, email FROM users WHERE name = '{username}'"\n    cursor.execute(query)\n    return cursor.fetchall()`
  },
  "c_overflow": {
    "title": "⚙️ C: Unbounded Buffer Overflow",
    "language": "C",
    "code": `#include <stdio.h>\n#include <string.h>\n\nvoid execute_task(char *input_str) {\n    char local_buf[16];\n    // Dangerous: gets and strcpy lack bounds checking\n    strcpy(local_buf, input_str);\n    printf("Result: %s\\n", local_buf);\n}\n\nint main() {\n    execute_task("This string exceeds sixteen bytes limit!");\n    return 0;\n}`
  },
  "java_resource": {
    "title": "☕ Java: Resource Leak & Concatenation",
    "language": "Java",
    "code": `import java.io.*;\n\npublic class FileParser {\n    public void dumpFile(String path) throws IOException {\n        // Resource leak: unclosed stream without try-with-resources\n        BufferedReader reader = new BufferedReader(new FileReader(path));\n        String line = reader.readLine();\n        System.out.println("First line: " + line);\n    }\n}`
  }
};

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND);
  const [backendStatus, setBackendStatus] = useState('checking'); // checking | online | offline
  const [showConfig, setShowConfig] = useState(false);
  const [languages, setLanguages] = useState(PRESET_LANGUAGES);
  const [selectedLanguage, setSelectedLanguage] = useState('Auto-Detect');
  const [samples, setSamples] = useState(FALLBACK_SAMPLES);
  const [selectedSampleKey, setSelectedSampleKey] = useState('');
  const [code, setCode] = useState(FALLBACK_SAMPLES.python_sqli.code);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [diffMode, setDiffMode] = useState('side-by-side');
  const [copyStatus, setCopyStatus] = useState('');

  // Check backend health and load samples
  useEffect(() => {
    checkBackendHealth(backendUrl);
  }, [backendUrl]);

  const checkBackendHealth = async (url) => {
    setBackendStatus('checking');
    try {
      const res = await fetch(`${url}/api/health`, { method: 'GET' });
      if (res.ok) {
        setBackendStatus('online');
        // Fetch languages and samples dynamically
        fetch(`${url}/api/languages`)
          .then(r => r.json())
          .then(data => { if (data.languages) setLanguages(data.languages); })
          .catch(() => {});

        fetch(`${url}/api/samples`)
          .then(r => r.json())
          .then(data => { if (data.samples) setSamples(data.samples); })
          .catch(() => {});
      } else {
        setBackendStatus('offline');
      }
    } catch (e) {
      setBackendStatus('offline');
    }
  };

  const handleSampleChange = (key) => {
    setSelectedSampleKey(key);
    if (samples[key]) {
      setCode(samples[key].code);
      if (samples[key].language) {
        setSelectedLanguage(samples[key].language);
      }
    }
  };

  const handleRunReview = async () => {
    if (!code.trim()) {
      setError('Please provide source code before initiating review.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${backendUrl}/api/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: code,
          language: selectedLanguage
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server responded with status ${response.status}`);
      }

      const data = await response.json();
      setReport(data);
      setActiveTab('overview');
    } catch (err) {
      setError(err.message || 'Failed to communicate with the review backend.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    setCopyStatus(label);
    setTimeout(() => setCopyStatus(''), 2500);
  };

  const downloadMarkdownReport = () => {
    if (!report || !report.markdown_report) return;
    const blob = new Blob([report.markdown_report], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `nexreview_${(report.language || 'analysis').toLowerCase()}_report.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Severity style helper
  const getSeverityBadge = (sev) => {
    const s = (sev || 'MEDIUM').toUpperCase();
    if (s === 'CRITICAL') return <span className="sev-badge sev-critical">🚨 Critical</span>;
    if (s === 'HIGH') return <span className="sev-badge sev-high">⚠️ High Priority</span>;
    if (s === 'MEDIUM') return <span className="sev-badge sev-medium">💡 Medium</span>;
    return <span className="sev-badge sev-low">ℹ️ Low / Style</span>;
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 20px 80px' }}>
      {/* Top Navbar */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'linear-gradient(135deg, #4F46E5, #06B6D4)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.3rem', boxShadow: '0 0 15px rgba(79, 70, 229, 0.4)' }}>
            ⚡
          </div>
          <div>
            <span style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.02em', color: '#F8FAFC' }}>NexReview</span>
            <span style={{ color: '#818CF8', fontWeight: 700, marginLeft: '4px' }}>AI</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Backend Status Pill */}
          <div 
            onClick={() => setShowConfig(!showConfig)}
            title="Click to configure backend URL"
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              padding: '6px 12px', 
              background: 'rgba(255,255,255,0.03)', 
              borderRadius: '9999px', 
              border: '1px solid rgba(255,255,255,0.08)',
              cursor: 'pointer',
              fontSize: '0.8rem',
              color: '#CBD5E1'
            }}
          >
            <span className={backendStatus === 'online' ? 'pulse-dot' : backendStatus === 'checking' ? 'pulse-dot-amber' : 'pulse-dot-red'} />
            <span>Render Backend: {backendStatus === 'online' ? 'Online' : backendStatus === 'checking' ? 'Connecting...' : 'Offline'}</span>
            <span style={{ color: '#64748B', fontSize: '0.75rem' }}>⚙️</span>
          </div>
        </div>
      </header>

      {/* Backend Settings Popover */}
      {showConfig && (
        <div className="glass-card" style={{ marginBottom: '20px', borderLeft: '4px solid #6366F1' }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', color: '#F1F5F9' }}>⚙️ Render Backend Configuration</h4>
          <p style={{ fontSize: '0.82rem', color: '#94A3B8', marginBottom: '12px' }}>
            Set the API endpoint for your deployed Render backend (e.g., <code>https://nexreview-backend.onrender.com</code>) or local backend (<code>http://localhost:8000</code>).
          </p>
          <div style={{ display: 'flex', gap: '8px', maxWidth: '600px' }}>
            <input 
              type="text" 
              value={backendUrl} 
              onChange={(e) => setBackendUrl(e.target.value)}
              placeholder="http://localhost:8000" 
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.15)',
                background: 'rgba(0,0,0,0.3)',
                color: '#F8FAFC',
                fontFamily: 'monospace',
                fontSize: '0.85rem'
              }}
            />
            <button className="btn-secondary" onClick={() => checkBackendHealth(backendUrl)}>Test Connection</button>
            <button className="btn-secondary" onClick={() => setShowConfig(false)}>Done</button>
          </div>
        </div>
      )}

      {/* Hero Banner */}
      <div className="hero-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
          <span className="pill-tag"><span className="pulse-dot"></span> Pipeline Ready</span>
          <span className="pill-tag" style={{ background: 'rgba(16,185,129,0.12)', color: '#6EE7B7', borderColor: 'rgba(16,185,129,0.3)' }}>Multi-Language Engine</span>
          <span className="pill-tag" style={{ background: 'rgba(244,63,94,0.12)', color: '#FDA4AF', borderColor: 'rgba(244,63,94,0.3)' }}>CWE Security Audit</span>
          <span className="pill-tag" style={{ background: 'rgba(192,132,252,0.12)', color: '#D8B4FE', borderColor: 'rgba(192,132,252,0.3)' }}>Vercel & Render Deployed</span>
        </div>
        <h1 className="hero-title">⚡ NexReview AI Agent</h1>
        <p style={{ color: '#94A3B8', fontSize: '1.02rem', maxWidth: '850px', lineHeight: 1.6, marginBottom: '14px' }}>
          Enterprise-grade code reviewer combining deep static AST analysis, security vulnerability auditing, 
          code smell diagnostics, algorithmic complexity modeling, and automated test & auto-fix diff synthesis.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {['Python', 'JavaScript', 'TypeScript', 'SQL', 'MongoDB', 'PHP', 'Java', 'C / C++', 'Perl', 'Go', 'Rust'].map((item) => (
            <span key={item} style={{ fontSize: '0.75rem', padding: '3px 9px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* Control Deck & Code Input */}
      <div className="glass-card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '16px' }}>
          {/* Target Language Dropdown */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: '#94A3B8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              🎯 Target Language
            </label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              style={{
                width: '100%',
                padding: '9px 12px',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                color: '#E2E8F0',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                fontSize: '0.9rem',
                outline: 'none'
              }}
            >
              {languages.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </div>

          {/* Quick Load Sample Dropdown */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: '#94A3B8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              📦 Quick Load Sample
            </label>
            <select
              value={selectedSampleKey}
              onChange={(e) => handleSampleChange(e.target.value)}
              style={{
                width: '100%',
                padding: '9px 12px',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                color: '#E2E8F0',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                fontSize: '0.9rem',
                outline: 'none'
              }}
            >
              <option value="">-- Choose Sample Snippet --</option>
              {Object.entries(samples).map(([key, sample]) => (
                <option key={key} value={key}>{sample.title}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Code Editor Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.82rem', color: '#94A3B8', fontWeight: 600 }}>Source Code Input</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.78rem' }} onClick={() => setCode('')}>
              Clear
            </button>
            <button className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.78rem' }} onClick={() => setCode(FALLBACK_SAMPLES.python_sqli.code)}>
              Reset Sample
            </button>
          </div>
        </div>

        {/* Code Textarea */}
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste or write code here (Python, JavaScript, SQL, C++, Java, etc.)..."
          rows={12}
          className="font-mono"
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '10px',
            background: 'rgba(5, 8, 16, 0.9)',
            color: '#F8FAFC',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            fontSize: '0.92rem',
            lineHeight: 1.5,
            outline: 'none',
            resize: 'vertical',
            marginBottom: '16px'
          }}
        />

        {/* Action Button & Status */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <button 
            className="btn-primary" 
            onClick={handleRunReview} 
            disabled={loading}
            style={{ minWidth: '240px' }}
          >
            {loading ? (
              <>
                <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⚙️</span>
                <span>Orchestrating Review Pipeline...</span>
              </>
            ) : (
              <>
                <span>🚀 Run Comprehensive Review</span>
              </>
            )}
          </button>

          <span style={{ fontSize: '0.8rem', color: '#64748B' }}>
            {code.length} characters • {code.split('\n').length} lines
          </span>
        </div>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px 16px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', color: '#FDA4AF', fontSize: '0.9rem' }}>
            ⚠️ <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      {/* Results Section */}
      {report && (
        <div style={{ marginTop: '32px' }}>
          {/* Critical Flaws Alert Banner */}
          {(report.has_fatal_syntax || (report.severity_counts && report.severity_counts.CRITICAL > 0)) && (
            <div style={{ background: 'rgba(244, 63, 94, 0.12)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '12px', padding: '14px 20px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '14px' }}>
              <span style={{ fontSize: '1.8rem' }}>🚨</span>
              <div>
                <strong style={{ color: '#FDA4AF', fontSize: '1.05rem' }}>Critical Flaws Detected</strong>
                <div style={{ color: '#CBD5E1', fontSize: '0.88rem', marginTop: '2px' }}>
                  The submitted code contains critical syntax errors or fatal vulnerabilities that prevent safe execution. Check the <strong>Logic & Bugs</strong> and <strong>Auto-Fix & Diff</strong> tabs for details.
                </div>
              </div>
            </div>
          )}

          {/* Executive Metrics Header */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            {/* Quality Score */}
            <div className="metric-card-pro">
              <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94A3B8', marginBottom: '6px' }}>Quality Score</div>
              <div className={report.quality_score >= 85 ? 'score-excellent-glow' : report.quality_score >= 60 ? 'score-warning-glow' : 'score-danger-glow'}>
                {report.quality_score}<span style={{ fontSize: '1.1rem', fontWeight: 500, color: '#64748B' }}>/100</span>
              </div>
              <div style={{ marginTop: '8px' }}>
                {report.quality_score >= 85 ? (
                  <span className="sev-badge" style={{ background: 'rgba(16,185,129,0.2)', color: '#6EE7B7', border: '1px solid #10B981' }}>🟢 Production Ready</span>
                ) : report.quality_score >= 60 ? (
                  <span className="sev-badge" style={{ background: 'rgba(245,158,11,0.2)', color: '#FDE047', border: '1px solid #F59E0B' }}>🟡 Needs Remediation</span>
                ) : (
                  <span className="sev-badge" style={{ background: 'rgba(244,63,94,0.2)', color: '#FDA4AF', border: '1px solid #F43F5E' }}>🔴 Critical Risk</span>
                )}
              </div>
            </div>

            {/* Language & Runtime */}
            <div className="metric-card-pro">
              <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94A3B8', marginBottom: '6px' }}>Language & Runtime</div>
              <div style={{ fontSize: '2.1rem', fontWeight: 800, color: '#38BDF8', margin: '4px 0' }}>{report.language}</div>
              <div style={{ fontSize: '0.82rem', color: '#A7F3D0' }}>{report.language_display || report.language}</div>
            </div>

            {/* Time Complexity */}
            <div className="metric-card-pro">
              <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94A3B8', marginBottom: '6px' }}>Time Complexity</div>
              <div style={{ fontSize: '2.0rem', fontWeight: 800, color: '#C084FC', margin: '4px 0' }}>{report.time_complexity || 'O(N)'}</div>
              <div style={{ fontSize: '0.78rem', color: '#94A3B8' }}>Algorithmic Scaling</div>
            </div>

            {/* Space Complexity */}
            <div className="metric-card-pro">
              <div style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94A3B8', marginBottom: '6px' }}>Space Complexity</div>
              <div style={{ fontSize: '2.0rem', fontWeight: 800, color: '#2DD4BF', margin: '4px 0' }}>{report.space_complexity || 'O(1)'}</div>
              <div style={{ fontSize: '0.78rem', color: '#94A3B8' }}>Memory Footprint</div>
            </div>
          </div>

          {/* Sub-Score Progress Bars */}
          {report.sub_scores && (
            <div className="glass-card" style={{ marginBottom: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                    <span style={{ fontWeight: 600 }}>Security Index</span>
                    <span style={{ color: '#38BDF8', fontWeight: 700 }}>{report.sub_scores.security}/100</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${report.sub_scores.security}%`, height: '100%', background: 'linear-gradient(90deg, #38BDF8, #6366F1)', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                    <span style={{ fontWeight: 600 }}>Maintainability Index</span>
                    <span style={{ color: '#A7F3D0', fontWeight: 700 }}>{report.sub_scores.maintainability}/100</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${report.sub_scores.maintainability}%`, height: '100%', background: 'linear-gradient(90deg, #10B981, #06B6D4)', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                    <span style={{ fontWeight: 600 }}>Performance Index</span>
                    <span style={{ color: '#FDE047', fontWeight: 700 }}>{report.sub_scores.performance}/100</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${report.sub_scores.performance}%`, height: '100%', background: 'linear-gradient(90deg, #F59E0B, #EC4899)', borderRadius: '4px' }} />
                  </div>
                </div>
              </div>

              {/* Severity Badges Row */}
              {report.severity_counts && (
                <div style={{ display: 'flex', gap: '10px', marginTop: '20px', flexWrap: 'wrap' }}>
                  <span className="sev-badge sev-critical">🚨 Critical ({report.severity_counts.CRITICAL || 0})</span>
                  <span className="sev-badge sev-high">⚠️ High Priority ({report.severity_counts.HIGH || 0})</span>
                  <span className="sev-badge sev-medium">💡 Medium ({report.severity_counts.MEDIUM || 0})</span>
                  <span className="sev-badge sev-low">ℹ️ Style / Low ({report.severity_counts.LOW || 0})</span>
                </div>
              )}
            </div>
          )}

          {/* Multi-Tab Deep Dive */}
          <div className="glass-card">
            {/* Tabs Header */}
            <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid rgba(255,255,255,0.08)', overflowX: 'auto', marginBottom: '20px' }}>
              <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
                📊 Executive Summary
              </button>
              <button className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`} onClick={() => setActiveTab('security')}>
                🛡️ Security Vulnerabilities ({report.security_issues ? report.security_issues.length : 0})
              </button>
              <button className={`tab-btn ${activeTab === 'bugs' ? 'active' : ''}`} onClick={() => setActiveTab('bugs')}>
                🐛 Logic & Bugs ({report.bugs ? report.bugs.length : 0})
              </button>
              <button className={`tab-btn ${activeTab === 'smells' ? 'active' : ''}`} onClick={() => setActiveTab('smells')}>
                🧹 Code Smells & Style ({((report.code_smells || []).length + (report.style_issues || []).length)})
              </button>
              <button className={`tab-btn ${activeTab === 'autofix' ? 'active' : ''}`} onClick={() => setActiveTab('autofix')}>
                🔄 Auto-Fix & Diff
              </button>
              <button className={`tab-btn ${activeTab === 'tests' ? 'active' : ''}`} onClick={() => setActiveTab('tests')}>
                🧪 Unit Tests
              </button>
              <button className={`tab-btn ${activeTab === 'practices' ? 'active' : ''}`} onClick={() => setActiveTab('practices')}>
                💡 Best Practices
              </button>
              <button className={`tab-btn ${activeTab === 'export' ? 'active' : ''}`} onClick={() => setActiveTab('export')}>
                📥 Export Report
              </button>
            </div>

            {/* Tab 1: Executive Overview */}
            {activeTab === 'overview' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '12px' }}>📋 Executive Summary</h3>
                <div style={{ background: 'rgba(99, 102, 241, 0.08)', borderLeft: '4px solid #6366F1', padding: '16px', borderRadius: '8px', lineHeight: 1.6, color: '#E2E8F0', marginBottom: '24px' }}>
                  {report.executive_summary}
                </div>

                <h3 style={{ fontSize: '1.1rem', color: '#F8FAFC', marginBottom: '12px' }}>⏱️ Algorithmic Complexity Breakdown</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                  <div className="issue-card" style={{ borderLeft: '4px solid #C084FC' }}>
                    <div style={{ fontWeight: 700, color: '#E2E8F0', marginBottom: '4px' }}>⏱️ Time Complexity</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#C084FC' }}>{report.time_complexity}</div>
                  </div>
                  <div className="issue-card" style={{ borderLeft: '4px solid #2DD4BF' }}>
                    <div style={{ fontWeight: 700, color: '#E2E8F0', marginBottom: '4px' }}>💾 Space Complexity</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#2DD4BF' }}>{report.space_complexity}</div>
                  </div>
                </div>

                {report.complexity_explanation && (
                  <div style={{ color: '#CBD5E1', fontSize: '0.9rem', lineHeight: 1.6 }}>
                    <strong>Detailed Complexity Rationale:</strong>
                    <p style={{ marginTop: '4px' }}>{report.complexity_explanation}</p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Security Vulnerabilities */}
            {activeTab === 'security' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '16px' }}>🛡️ Security Vulnerability Audit</h3>
                {(!report.security_issues || report.security_issues.length === 0) ? (
                  <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', color: '#6EE7B7' }}>
                    ✅ Clean security audit! No critical vulnerabilities or injection vectors detected.
                  </div>
                ) : (
                  report.security_issues.map((issue, idx) => (
                    <div key={idx} className="issue-card" style={{ borderLeft: `4px solid ${issue.severity === 'CRITICAL' ? '#F43F5E' : issue.severity === 'HIGH' ? '#F97316' : '#EAB308'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#F8FAFC' }}>{issue.title}</span>
                          {issue.line && (
                            <span className="pill-tag" style={{ background: 'rgba(255,255,255,0.08)', color: '#CBD5E1', fontSize: '0.75rem' }}>
                              📍 Line {issue.line}
                            </span>
                          )}
                        </div>
                        {getSeverityBadge(issue.severity)}
                      </div>
                      <p style={{ margin: '8px 0', color: '#CBD5E1', fontSize: '0.92rem' }}>{issue.description}</p>
                      {issue.cwe && (
                        <div style={{ fontSize: '0.82rem', color: '#94A3B8', marginBottom: '6px' }}>
                          <strong>CWE Reference:</strong> <code style={{ color: '#FCA5A5' }}>{issue.cwe}</code>
                        </div>
                      )}
                      <div style={{ marginTop: '6px', fontSize: '0.88rem', color: '#6EE7B7', background: 'rgba(16,185,129,0.06)', padding: '8px 12px', borderRadius: '6px' }}>
                        <strong>Remediation:</strong> {issue.recommendation}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 3: Logic & Bugs */}
            {activeTab === 'bugs' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '16px' }}>🐛 Logic & Runtime Anomalies</h3>
                {(!report.bugs || report.bugs.length === 0) ? (
                  <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', color: '#6EE7B7' }}>
                    ✅ No logic flaws or syntax errors detected.
                  </div>
                ) : (
                  report.bugs.map((bug, idx) => (
                    <div key={idx} className="issue-card" style={{ borderLeft: `4px solid ${bug.severity === 'CRITICAL' ? '#F43F5E' : bug.severity === 'HIGH' ? '#F97316' : '#38BDF8'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#F8FAFC' }}>{bug.title}</span>
                          {bug.line && (
                            <span className="pill-tag" style={{ background: 'rgba(255,255,255,0.08)', color: '#CBD5E1', fontSize: '0.75rem' }}>
                              📍 Line {bug.line}{bug.column ? `, Col ${bug.column}` : ''}
                            </span>
                          )}
                        </div>
                        {getSeverityBadge(bug.severity)}
                      </div>
                      <p style={{ margin: '8px 0', color: '#CBD5E1', fontSize: '0.92rem' }}>{bug.description}</p>
                      {bug.code_snippet && (
                        <div style={{ margin: '8px 0', padding: '8px 12px', background: 'rgba(0,0,0,0.4)', borderLeft: '2px solid #38BDF8', borderRadius: '4px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#F1F5F9' }}>
                          <code>{bug.code_snippet}</code>
                        </div>
                      )}
                      <div style={{ marginTop: '6px', fontSize: '0.88rem', color: '#93C5FD', background: 'rgba(59,130,246,0.06)', padding: '8px 12px', borderRadius: '6px' }}>
                        <strong>Resolution:</strong> {bug.recommendation}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 4: Code Smells & Style */}
            {activeTab === 'smells' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '16px' }}>🧹 Architectural & Cognitive Smells</h3>
                {(!report.code_smells || report.code_smells.length === 0) ? (
                  <div style={{ padding: '14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', color: '#94A3B8', marginBottom: '20px' }}>
                    ✅ No architectural code smells detected.
                  </div>
                ) : (
                  report.code_smells.map((sm, idx) => (
                    <div key={idx} className="issue-card" style={{ borderLeft: '4px solid #FDE047' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, color: '#F8FAFC', fontSize: '1rem' }}>💡 {sm.title}</span>
                        {getSeverityBadge(sm.severity || 'MEDIUM')}
                      </div>
                      <p style={{ margin: '6px 0', color: '#CBD5E1', fontSize: '0.9rem' }}>{sm.description}</p>
                      <div style={{ fontSize: '0.85rem', color: '#6EE7B7' }}>
                        <strong>Refactoring Tip:</strong> {sm.recommendation}
                      </div>
                    </div>
                  ))
                )}

                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', margin: '24px 0 16px' }}>🎨 Code Style & Conventions</h3>
                {(!report.style_issues || report.style_issues.length === 0) ? (
                  <div style={{ padding: '14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', color: '#94A3B8' }}>
                    ✅ Clean code formatting and convention conformance.
                  </div>
                ) : (
                  report.style_issues.map((st, idx) => (
                    <div key={idx} style={{ padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderLeft: '3px solid #38BDF8', marginBottom: '8px', borderRadius: '4px', fontSize: '0.88rem' }}>
                      <strong style={{ color: '#38BDF8' }}>{st.rule}:</strong> <span style={{ color: '#CBD5E1' }}>{st.description}</span>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 5: Auto-Fix & Diff */}
            {activeTab === 'autofix' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
                  <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', margin: 0 }}>🔄 Automated Code Fix & Diff Comparison</h3>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      className={`btn-secondary ${diffMode === 'side-by-side' ? 'active' : ''}`}
                      onClick={() => setDiffMode('side-by-side')}
                      style={{ background: diffMode === 'side-by-side' ? 'rgba(99, 102, 241, 0.2)' : undefined, borderColor: diffMode === 'side-by-side' ? '#6366F1' : undefined }}
                    >
                      Side-by-Side
                    </button>
                    <button 
                      className={`btn-secondary ${diffMode === 'unified' ? 'active' : ''}`}
                      onClick={() => setDiffMode('unified')}
                      style={{ background: diffMode === 'unified' ? 'rgba(99, 102, 241, 0.2)' : undefined, borderColor: diffMode === 'unified' ? '#6366F1' : undefined }}
                    >
                      Unified Diff
                    </button>
                    <button 
                      className="btn-secondary" 
                      onClick={() => copyToClipboard(report.suggested_fix, 'fix')}
                    >
                      {copyStatus === 'fix' ? '✅ Copied!' : '📋 Copy Fix'}
                    </button>
                  </div>
                </div>

                {diffMode === 'side-by-side' ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FDA4AF', marginBottom: '6px' }}>❌ Original Code (Before)</div>
                      <pre className="font-mono" style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(244, 63, 94, 0.25)', padding: '14px', borderRadius: '8px', fontSize: '0.85rem', overflowX: 'auto', maxHeight: '420px', whiteSpace: 'pre-wrap' }}>
                        {code}
                      </pre>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#6EE7B7', marginBottom: '6px' }}>✅ Auto-Fixed Code (After)</div>
                      <pre className="font-mono" style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '14px', borderRadius: '8px', fontSize: '0.85rem', overflowX: 'auto', maxHeight: '420px', whiteSpace: 'pre-wrap' }}>
                        {report.suggested_fix}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#CBD5E1', marginBottom: '6px' }}>🔀 Unified Line Diff</div>
                    <pre className="font-mono" style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.1)', padding: '14px', borderRadius: '8px', fontSize: '0.85rem', overflowX: 'auto', maxHeight: '420px', color: '#93C5FD' }}>
                      {report.unified_diff || 'No line alterations detected.'}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Tab 6: Unit Tests */}
            {activeTab === 'tests' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
                  <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', margin: 0 }}>🧪 Generated Test Suite ({report.language})</h3>
                  <button 
                    className="btn-secondary" 
                    onClick={() => copyToClipboard(report.test_cases, 'tests')}
                  >
                    {copyStatus === 'tests' ? '✅ Copied!' : '📋 Copy Tests'}
                  </button>
                </div>
                <p style={{ fontSize: '0.88rem', color: '#94A3B8', marginBottom: '12px' }}>
                  Autonomous unit tests covering standard cases, edge bounds, and negative assertions:
                </p>
                <pre className="font-mono" style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.1)', padding: '16px', borderRadius: '8px', fontSize: '0.85rem', overflowX: 'auto', maxHeight: '500px', whiteSpace: 'pre-wrap', color: '#A5B4FC' }}>
                  {report.test_cases}
                </pre>
              </div>
            )}

            {/* Tab 7: Best Practices */}
            {activeTab === 'practices' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '16px' }}>💡 Senior Engineering Recommendations</h3>
                {(!report.best_practices || report.best_practices.length === 0) ? (
                  <p style={{ color: '#94A3B8' }}>No extra guidelines for this snippet.</p>
                ) : (
                  report.best_practices.map((bp, idx) => (
                    <div key={idx} style={{ padding: '12px 16px', background: 'rgba(255,255,255,0.02)', borderLeft: '3px solid #818CF8', borderRadius: '6px', marginBottom: '10px', color: '#E2E8F0', fontSize: '0.92rem', lineHeight: 1.6 }}>
                      {bp}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 8: Export Report */}
            {activeTab === 'export' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#F8FAFC', marginBottom: '16px' }}>📥 Download & Export Full Report</h3>
                <p style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '16px' }}>
                  Export the complete static, security, code smell, and AI evaluation report as an enterprise Markdown document.
                </p>
                <button className="btn-primary" onClick={downloadMarkdownReport} style={{ marginBottom: '20px' }}>
                  📄 Download Full Markdown Report (.md)
                </button>
                <h4 style={{ fontSize: '0.95rem', color: '#CBD5E1', marginBottom: '8px' }}>Markdown Report Preview:</h4>
                <pre className="font-mono" style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.08)', padding: '16px', borderRadius: '8px', fontSize: '0.82rem', overflowX: 'auto', maxHeight: '400px', whiteSpace: 'pre-wrap', color: '#CBD5E1' }}>
                  {report.markdown_report}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
