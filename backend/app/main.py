import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db, llm, services
from app.knowledge import CATEGORIES, WARDS
from app.ml.engine import engine

MODEL_METRICS = Path(__file__).resolve().parents[1] / "models" / "metrics.json"
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_):
    db.init()
    services.seed_if_empty()
    yield


app = FastAPI(title="SamajSevak API", version="1.0.0",
              description="AI-powered public grievance analysis & resolution recommendation platform",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AnalyzeIn(BaseModel):
    text: str = Field(min_length=10, max_length=3000)
    ward: Optional[str] = None


class GrievanceIn(AnalyzeIn):
    citizen_name: Optional[str] = None
    phone: Optional[str] = None
    channel: str = "Web"


class UpdateIn(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_note: Optional[str] = None


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    metrics = json.loads(MODEL_METRICS.read_text()) if MODEL_METRICS.exists() else {}
    metrics.pop("report", None)
    return {"categories": {k: {"department": v["department"], "sla_hours": v["sla_hours"]} for k, v in CATEGORIES.items()},
            "wards": list(WARDS), "statuses": services.STATUSES, "llm_provider": llm.provider(), "model_metrics": metrics}


@app.post("/api/analyze")
def analyze(body: AnalyzeIn):
    """Real-time AI analysis preview (nothing is saved)."""
    return engine.analyze(body.text, body.ward)


@app.post("/api/grievances")
def create(body: GrievanceIn):
    return services.create_grievance(body.text, body.ward, body.citizen_name, body.phone, body.channel)


@app.get("/api/grievances")
def list_(status: str = None, category: str = None, priority: str = None, ward: str = None, q: str = None, limit: int = 200):
    return services.list_grievances(status, category, priority, ward, q, limit)


@app.get("/api/grievances/{gid}")
def get(gid: str):
    g = services.get_grievance(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    # refresh similar cases against the live index
    g["live_similar"] = engine.analyze(g["text"], g["ward"], exclude_id=gid)["similar_cases"]
    return g


@app.patch("/api/grievances/{gid}")
def update(gid: str, body: UpdateIn):
    if body.status and body.status not in services.STATUSES:
        raise HTTPException(400, "Invalid status")
    g = services.update_grievance(gid, body.status, body.note, body.assigned_to, body.resolution_note)
    if not g:
        raise HTTPException(404, "Grievance not found")
    return g


@app.post("/api/grievances/{gid}/feedback")
def rate(gid: str, body: FeedbackIn):
    if not services.get_grievance(gid):
        raise HTTPException(404, "Grievance not found")
    return services.feedback(gid, body.rating)


@app.post("/api/grievances/{gid}/draft")
def draft(gid: str):
    g = services.get_grievance(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    return llm.draft(g)


@app.get("/api/stats")
def stats():
    return services.stats()


@app.get("/api/analytics")
def analytics():
    return services.analytics()


@app.get("/api/hotspots")
def hotspots():
    return services.hotspots()


@app.get("/api/alerts")
def alerts():
    return services.alerts()


# Serve built React app (single-command deployment)
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
