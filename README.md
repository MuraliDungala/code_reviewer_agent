# ⚡ NexReview AI | Intelligent Multi-Engine Code Reviewer

Enterprise-grade code review pipeline combining deep static AST analysis, CWE security vulnerability auditing, architectural code smell diagnostics, algorithmic complexity modeling (Big-O), and autonomous unit test & auto-fix diff synthesis.

---

## 🏗️ Architecture & Deployment Overview

This project is architected with a modern decoupled structure, optimized for seamless cloud deployment:

```
code_reviewer_agent/
├── backend/                  # 🚀 FastAPI REST API (Deployed to Render)
│   ├── agents/               # Style, Test Generator, and Auto-Fix Agents
│   ├── llm/                  # Groq & LangChain Orchestrator
│   ├── reviewers/            # Static, Security, and Code Smell Analyzers
│   ├── main.py               # FastAPI application with CORS & endpoints
│   ├── Procfile              # Render start process definition
│   ├── render.yaml           # Render Infrastructure-as-Code blueprint
│   ├── requirements.txt      # Python dependencies for Render
│   └── .env.example          # Sample environment variables
│
├── frontend/                 # 🌐 Modern Web UI (Deployed to Vercel)
│   ├── index.html            # Ultra-fast responsive UI with Glassmorphic styling
│   ├── app.js                # Dynamic review controller, state management, & tabs
│   ├── style.css             # Cyberpunk/Dark theme, glowing metric cards, & badges
│   ├── vercel.json           # Vercel deployment configuration & routing
│   └── .env.example          # Frontend configuration for Render API URL
│
└── code_reviewer_agent/      # ⚡ Original Streamlit application (Preserved)
    ├── app.py                # Full-featured Streamlit dashboard
    └── requirements.txt      # Streamlit dependencies
```

---

## 🚀 Part 1: Running the Project Locally

### Option A: Run FastAPI + Modern Frontend (Recommended)

1. Double-click **`run_backend.bat`** OR execute in your terminal:
   ```powershell
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Open your browser:
   - **Frontend App**: [http://localhost:8000](http://localhost:8000)
   - **Swagger Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Healthcheck Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Option B: Run Streamlit UI

1. Double-click **`run_streamlit.bat`** OR execute:
   ```powershell
   cd code_reviewer_agent
   streamlit run app.py
   ```
2. Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Part 2: Deploying Backend to Render

### Step 1: Push Project to GitHub

1. Initialize git and commit:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: NexReview AI Backend & Frontend"
   ```
2. Create a repository on GitHub (e.g. `nexreview-ai`) and push:
   ```bash
   git remote add origin https://github.com/<your-username>/nexreview-ai.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Create Web Service on Render

1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** ➔ **Web Service**.
3. Connect your GitHub repository (`nexreview-ai`).
4. Configure the service settings:
   - **Name**: `nexreview-backend` (or any name you choose)
   - **Region**: Choose the closest region (e.g., Oregon, Frankfurt, Singapore)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. Under **Environment Variables**, add:
   - `GROQ_API_KEY`: `<Your-Groq-API-Key>`
   - `GEMINI_API_KEY`: `<Your-Gemini-API-Key>` (Optional)
   - `PYTHON_VERSION`: `3.10.12`
6. Click **Create Web Service**.
7. Render will build and deploy your backend. Once complete, copy your live Render URL:
   `https://nexreview-backend.onrender.com`

---

## 🌐 Part 3: Deploying Frontend to Vercel

### Method A: Via Vercel Dashboard (Recommended)

1. Log into your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** ➔ **Project**.
3. Import your GitHub repository (`nexreview-ai`).
4. In the configuration screen:
   - **Project Name**: `nexreview-frontend`
   - **Framework Preset**: `Other`
   - **Root Directory**: Click *Edit* and select **`frontend`**
5. Expand **Environment Variables**:
   - Key: `VITE_BACKEND_URL`
   - Value: `https://nexreview-backend.onrender.com` *(Your live Render backend URL from Part 2)*
6. Click **Deploy**.
7. Vercel will deploy your frontend in seconds and provide your live URL:
   `https://nexreview-frontend.vercel.app`

### Method B: Via Vercel CLI

```bash
# Navigate to the frontend directory
cd frontend

# Deploy directly using Vercel CLI
npx vercel --prod
```

---

## 🔗 Part 4: Connecting Frontend & Backend

1. When your Vercel frontend is loaded, it automatically routes review requests to your Render backend.
2. You can also change or test the backend URL directly in the live web app:
   - Click the **Backend Status Pill** in the top right corner.
   - Enter your Render backend URL (e.g., `https://nexreview-backend.onrender.com`).
   - Click **Test Connection** ➔ **Save**.
   - Your choice is saved in `localStorage` so it persists across refreshes!

---

## 🛡️ API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the frontend web dashboard |
| `GET` | `/api/health` | Healthcheck, model configuration, & API readiness |
| `GET` | `/api/languages` | List of 18+ supported languages & detection presets |
| `GET` | `/api/samples` | Pre-configured vulnerable / smelly code snippets |
| `POST` | `/api/review` | Main multi-stage review orchestrator |
| `GET` | `/docs` | Swagger interactive API documentation |

### Example Review Request:
```bash
curl -X POST "https://nexreview-backend.onrender.com/api/review" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SELECT * FROM users u, accounts a WHERE u.id = a.user_id;",
    "language": "SQL"
  }'
```

---

## 👨‍💻 Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, LangChain, Groq SDK (Qwen 2.5 72B / Llama 3.3 70B), Flake8, Black.
- **Frontend**: HTML5, Vanilla ES6+, CSS3 Glassmorphism, JetBrains Mono, KaTeX/Markdown export.
- **Hosting**: Render (Web Service), Vercel (Edge CDN).
