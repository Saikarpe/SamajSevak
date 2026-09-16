# SamajSevak — AI-Powered Public Grievance Intelligence Platform

> **Hack2Ignite · Problem Statement AI-04:** Design an AI-powered public grievance analysis and resolution recommendation platform.

SamajSevak turns raw citizen complaints (English, Hindi, Hinglish; web, app, WhatsApp, call centre) into **prioritised, routed and actionable cases** — and tells officers *how* to resolve them, based on SOPs and what worked for similar past cases.

![Command Center](docs/screenshots/dashboard.png)

## ✨ Key features

| For citizens | For officers / administrators |
|---|---|
| Raise grievance in free text or **voice** | **Command Center**: KPIs, 30‑day trend, AI alerts |
| **Live AI preview** while typing (department, priority, ETA) | **Priority queue** ranked by explainable AI score |
| Tracking ID, status timeline, SLA | **Grievance detail** with AI triage, "why this priority", duplicates |
| Rate the resolution (feedback loop) | **Recommended resolution plan** + proven past actions + ETA |
| | **AI-drafted citizen reply** (Gemini/OpenAI, offline template fallback) |
| | **Hotspot map**, ward risk ranking, department SLA performance |
| | **Emerging-issue detection** (spike vs baseline → root-cause alert) |

## 🧠 AI pipeline

1. **Clean** – strip greetings/boilerplate, handle Hinglish.
2. **Classify & route** – TF‑IDF (word 1–2 grams + char 3–5 grams) → Logistic Regression across 11 categories → department + SLA. Low confidence (<40%) → human triage.
3. **Entity extraction** – ward, landmark, duration, risk keywords, vulnerable groups.
4. **Sentiment & distress** – lexicon + intensifiers + punctuation/caps signals.
5. **Duplicate detection** – cosine similarity, category-aware re-ranking, same-ward open cases.
6. **Explainable priority (0–100)** – severity + risk terms + vulnerability + distress + duration + cluster size + repeat complaint; every point is shown to the officer.
7. **Resolution recommendation** – context-ranked SOP playbook + retrieval of what resolved similar cases + median historical resolution time → ETA + inter-department coordination.
8. **Emerging issue detection** – ward × category volume in last 7 days vs 3‑week baseline (≥2× and ≥4 cases) + SLA-breach escalation.
9. **GenAI assist (optional)** – LLM drafts empathetic, grounded replies.

Classifier: 100% on the synthetic test split and **95.5% on a hand-written holdout of 22 unseen complaints** (`backend/models/metrics.json`). The synthetic data is a stand-in; in production it retrains on officer-corrected labels.

## 🏗 Architecture

```mermaid
flowchart LR
  A[Citizen: Web / App / WhatsApp / Voice] --> B[React + Vite UI]
  B -->|REST| C[FastAPI]
  C --> D[AI Engine\nclassifier · sentiment · NER\npriority · similarity · recommender]
  C --> E[(SQLite / PostgreSQL)]
  D --> F[(Knowledge base\nSOP playbooks · SLAs · past resolutions)]
  C -. optional .-> G[Gemini / OpenAI]
  C --> H[Analytics · Hotspots · Alerts]
  H --> I[Officer Console]
```

## 🛠 Tech stack
- **Frontend:** React 19, Vite, React Router, Recharts, Leaflet (OpenStreetMap), lucide-react
- **Backend:** Python 3.11, FastAPI, Uvicorn, SQLite
- **ML/NLP:** scikit-learn (TF‑IDF, Logistic Regression, cosine similarity), NumPy, joblib
- **GenAI (optional):** Google Gemini 2.0 Flash / OpenAI GPT-4o-mini via httpx
- **DevOps:** Docker (single container), pytest

## 🚀 Run locally

**Backend** (Python 3.10+):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.ml.train          # optional, a trained model is already included
uvicorn app.main:app --reload --port 8000
```
The first start seeds ~450 realistic historical grievances. API docs: http://localhost:8000/docs

**Frontend** (Node 18+), in a second terminal:
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

**Single command (Docker):**
```bash
docker build -t samajsevak . && docker run -p 8000:8000 samajsevak   # http://localhost:8000
```

**Optional LLM:** set `GEMINI_API_KEY` or `OPENAI_API_KEY` before starting the backend.

**Tests:** `cd backend && pytest -q`

## 📡 API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/analyze` | Live AI analysis (no save) |
| POST | `/api/grievances` | Register grievance (auto-triage & route) |
| GET | `/api/grievances` | Filterable priority queue |
| GET | `/api/grievances/{id}` | Detail, AI analysis, timeline |
| PATCH | `/api/grievances/{id}` | Assign / update status / resolve |
| POST | `/api/grievances/{id}/feedback` | Citizen rating |
| POST | `/api/grievances/{id}/draft` | AI citizen reply |
| GET | `/api/stats` · `/api/analytics` · `/api/hotspots` · `/api/alerts` | Dashboards & insights |

## 🗺 Roadmap
Transformer (IndicBERT/MuRIL) multilingual classifier · image evidence analysis (pothole/garbage detection) · WhatsApp bot · officer-feedback retraining · PostgreSQL + PostGIS · CPGRAMS/municipal system integration.

## 📁 Structure
```
backend/app/        FastAPI app, services, knowledge base, LLM helper
backend/app/ml/     dataset generator, training, AI engine
backend/models/     trained classifier + metrics
frontend/src/       React pages & components
docs/               presentation
```
