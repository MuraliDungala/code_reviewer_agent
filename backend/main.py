import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables robustly
dotenv_paths = [
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "code_reviewer_agent", ".env")
]
for p in dotenv_paths:
    if os.path.exists(p):
        load_dotenv(p)

# Import the orchestrator review engine
from llm.orchestrator import review_code_orchestrated, SUPPORTED_LANGUAGES

app = FastAPI(
    title="NexReview AI API",
    description="Intelligent Multi-Engine Code Reviewer Backend API for Render",
    version="1.0.0"
)

# Enable CORS for Vercel, localhost, and custom domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_SNIPPETS: Dict[str, Dict[str, str]] = {
    "python_sqli": {
        "title": "🐍 Python: Dynamic SQL Injection",
        "language": "Python",
        "code": """import sqlite3

def fetch_user_record(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # High Risk: Dynamic f-string allows SQL injection
    query = f"SELECT id, username, email FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()"""
    },
    "sql_cartesian": {
        "title": "🗄️ SQL: Unindexed Cartesian Join & DELETE",
        "language": "SQL",
        "code": """-- Critical: Unconditional DELETE + Wildcard Join
DELETE FROM audit_logs;

SELECT * 
FROM users u, transactions t, accounts a
WHERE u.status = 'active'
ORDER BY t.created_at DESC;"""
    },
    "mongo_injection": {
        "title": "🍃 MongoDB: NoSQL $where Injection",
        "language": "MongoDB",
        "code": """// NoSQL Injection via $where + Unbounded Query
const targetName = req.body.username;

db.users.find({
    $where: "this.username == '" + targetName + "'"
});

// Dangerous unbounded fetch
const allRecords = db.audit_trails.find({});"""
    },
    "perl_open": {
        "title": "🐪 Perl: Two-Argument open() Vulnerability",
        "language": "Perl",
        "code": """#!/usr/bin/perl
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

read_user_file("data.txt");"""
    },
    "php_scope": {
        "title": "🐘 PHP: Zero Division & Broken Scope",
        "language": "PHP",
        "code": """<?php
$numbers = [10, 20, 30, 40, 50];

for ($i = 0; $i < count($numbers); $i++) {
    $total += $numbers[$i];
}

$average = $total / 0;

echo "Average: " . calculateAverage($numbers);
?>"""
    },
    "js_xss": {
        "title": "⚡ JavaScript: DOM XSS & Loose Coercion",
        "language": "JavaScript",
        "code": """// DOM XSS via innerHTML and loose equality
function renderUserProfile(userData) {
    const userRole = userData.role;
    
    // Loose equality hazard
    if (userRole == "admin") {
        document.getElementById("badge").innerHTML = "<b>" + userData.name + "</b>";
    }
    
    let total = 0;
    let avg = total / 0;
    console.log("Average:", avg);
}"""
    },
    "c_overflow": {
        "title": "⚙️ C: Unbounded Buffer Overflow",
        "language": "C",
        "code": """#include <stdio.h>
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
}"""
    },
    "java_resource": {
        "title": "☕ Java: Resource Leak & Concatenation",
        "language": "Java",
        "code": """import java.io.*;

public class FileParser {
    public void dumpFile(String path) throws IOException {
        // Resource leak: unclosed stream without try-with-resources
        BufferedReader reader = new BufferedReader(new FileReader(path));
        String line = reader.readLine();
        System.out.println("First line: " + line);
    }
}"""
    }
}

class ReviewRequest(BaseModel):
    code: str
    language: Optional[str] = "Auto-Detect"

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "NexReview AI Backend",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    }

@app.get("/api/languages")
def get_languages():
    languages = ["Auto-Detect"] + SUPPORTED_LANGUAGES
    return {"languages": languages}

@app.get("/api/samples")
def get_samples():
    return {"samples": SAMPLE_SNIPPETS}

@app.post("/api/review")
def review_code(req: ReviewRequest):
    if not req.code or not req.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source code cannot be empty."
        )

    try:
        report = review_code_orchestrated(req.code, req.language or "Auto-Detect")
        if "error" in report and report["error"] and not report.get("quality_score"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=report["error"]
            )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review engine failed: {str(e)}"
        )

# Mount frontend static directory if present
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir) and os.path.exists(os.path.join(frontend_dir, "index.html")):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "message": "⚡ NexReview AI Backend is online",
            "status": "online",
            "docs": "/docs",
            "groq_configured": bool(os.getenv("GROQ_API_KEY"))
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
