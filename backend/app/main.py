import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import auth, db, llm, services
from app.knowledge import CATEGORIES, ESCALATION_STAGES, WARDS
from app.ml import embed, train
from app.ml.engine import engine

MODEL_METRICS = Path(__file__).resolve().parents[1] / "models" / "metrics.json"
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
Officer = Depends(auth.require_officer)
Citizen = Depends(auth.optional_citizen)


def _visible(gid: str, officer: dict):
    """The report, if this officer may open it: a department head only sees its own department's
    issues while they are at the Complaint / Warning stage (afterwards they are with the strike bodies)."""
    g = services.get_grievance(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    if not services.visible(g, auth.scope(officer)):
        raise HTTPException(403, "This issue is not with your department at its current stage")
    return g


@asynccontextmanager
async def lifespan(_):
    db.init()
    auth.ensure_officer()
    services.seed_if_empty()
    services.purge_ip_hashes()
    services.tick()
    yield


app = FastAPI(title="SamajSevak API", version="1.2.0",
              description="AI-powered public grievance analysis, resolution recommendation and accountability platform",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AnalyzeIn(BaseModel):
    text: str = Field(min_length=10, max_length=3000)
    ward: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    citizen_category: Optional[str] = None  # the citizen's own choice; None = let the AI decide

    def point(self):
        return (self.lat, self.lng) if self.lat is not None and self.lng is not None else None

    def category(self):
        if self.citizen_category and self.citizen_category not in CATEGORIES:
            raise HTTPException(400, "Invalid category")
        return self.citizen_category or None


class GrievanceIn(AnalyzeIn):
    citizen_name: Optional[str] = None
    phone: Optional[str] = None
    channel: str = "Web"
    geo_source: Literal["gps", "pin"] = "gps"
    photo: Optional[str] = Field(None, max_length=4_200_000)  # base64 / data URL, 3 MB decoded
    join_issue: Optional[str] = None  # tracking ID of the existing issue the citizen chose to join
    shown_issues: list[str] = Field(default_factory=list, max_length=5)  # suggested but not joined


class UpdateIn(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_note: Optional[str] = None
    category: Optional[str] = None
    resolution_photo: Optional[str] = Field(None, max_length=4_200_000)
    master_id: Optional[str] = None  # link this report to that issue; its own id detaches it


class FeedbackIn(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    satisfied: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=500)


class GroundIn(BaseModel):
    answer: Literal["yes", "partly", "no"]  # is work happening on the ground at this stage?
    comment: Optional[str] = Field(None, max_length=500)
    photo: Optional[str] = Field(None, max_length=4_200_000)


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class CitizenIn(BaseModel):
    name: str = Field(max_length=80)
    phone: str = Field(max_length=20)


def _photo(data: Optional[str]):
    try:
        return services.decode_photo(data) if data else None
    except ValueError as e:
        raise HTTPException(400, str(e))


def _metrics():
    metrics = json.loads(MODEL_METRICS.read_text(encoding="utf-8")) if MODEL_METRICS.exists() else {}
    metrics.pop("report", None)
    return metrics


# ---------------- public (citizen) ----------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return {"categories": {k: {"department": v["department"], "sla_hours": v["sla_hours"]} for k, v in CATEGORIES.items()},
            "wards": list(WARDS), "ward_centers": WARDS, "statuses": services.STATUSES, "llm_provider": llm.provider(),
            "stages": [{"stage": s, "authority": who} for s, who, _ in ESCALATION_STAGES],
            "embeddings": embed.available(), "model_metrics": _metrics(),
            # only present while no OFFICER_PASSWORD is configured (hosted demo)
            "demo_login": {"username": auth.DEMO_USER, "password": auth.DEMO_PASSWORD} if auth.is_demo() else None,
            "demo_staff": [{k: a[k] for k in ("username", "name", "role", "department")} for a in auth.staff_accounts()]
                          if auth.is_demo() else None}


@app.post("/api/auth/login")
def login(body: LoginIn):
    return auth.login(body.username, body.password)


@app.get("/api/auth/me")
def me(officer: dict = Officer):
    return {"username": officer["u"], "name": officer["n"], "role": officer.get("r", "admin"), "department": officer.get("d")}


@app.post("/api/citizen/login")
def citizen_login(body: CitizenIn):
    """Name + mobile number. Creates the account on first use."""
    try:
        return services.citizen_login(body.name, body.phone)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/citizen/grievances")
def my_grievances(citizen: Optional[dict] = Citizen):
    if not citizen:
        raise HTTPException(401, auth.CITIZEN_EXPIRED)
    services.tick()
    return services.citizen_grievances(citizen["c"])


@app.post("/api/analyze")
def analyze(body: AnalyzeIn, officer: Optional[dict] = Depends(auth.optional_officer)):
    """Real-time AI analysis preview (nothing is saved), plus open issues this may already be about."""
    a = engine.analyze(body.text, body.ward, point=body.point(), category=body.category())
    a["existing_issues"] = services.issue_cards(body.text, a["category"], a["ward"], body.point())
    if not officer:  # citizens learn that a similar case exists, not what other people wrote
        for s in a["similar_cases"] + a["possible_duplicates"]:
            s["title"], s["resolution_note"] = s["category"], None
    return a


@app.post("/api/grievances")
def create(body: GrievanceIn, request: Request, tasks: BackgroundTasks,
           citizen: Optional[dict] = Depends(auth.citizen_or_anonymous)):
    g = services.create_grievance(
        body.text, body.ward, body.citizen_name, body.phone, body.channel, point=body.point(), geo_source=body.geo_source,
        photo=_photo(body.photo), citizen_id=citizen and citizen["c"], citizen_category=body.category(),
        join_issue=body.join_issue, shown_issues=body.shown_issues, ip=request.client and request.client.host)
    if g["photo"] and llm.provider():
        tasks.add_task(services.check_photo, g["id"])
    return {k: g[k] for k in ("id", "department", "priority_level", "category", "ward", "status", "language",
                              "master_id", "association_source", "report_count", "stage")}


@app.get("/api/track/{gid}")
def track(gid: str):
    services.tick()
    g = services.track(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    return g


@app.get("/api/track/{gid}/resolution-photo")
def resolution_photo(gid: str):
    f = services.photo_file(gid, "resolution")
    if not f:
        raise HTTPException(404, "No resolution photo")
    return FileResponse(f[0], media_type=f[1])


@app.post("/api/grievances/{gid}/feedback")
def rate(gid: str, body: FeedbackIn, citizen: Optional[dict] = Citizen):
    """Satisfied / not satisfied, rating and comment on the citizen's own report."""
    g = services.get_grievance(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    if g["citizen_id"] and (not citizen or citizen["c"] != g["citizen_id"]):
        raise HTTPException(403, "Sign in as the citizen who filed this report to respond")
    if g["status"] not in services.DONE:
        raise HTTPException(400, "Feedback opens once the grievance is resolved")
    return services.track(services.feedback(gid, body.rating, body.satisfied, body.comment)["id"])


@app.post("/api/grievances/{gid}/ground")
def ground(gid: str, body: GroundIn, citizen: Optional[dict] = Citizen):
    """At any open stage the citizen says whether work is happening on the ground."""
    g = services.get_grievance(gid)
    if not g:
        raise HTTPException(404, "Grievance not found")
    if g["citizen_id"] and (not citizen or citizen["c"] != g["citizen_id"]):
        raise HTTPException(403, "Sign in as the citizen who filed this report to respond")
    try:
        services.ground_report(gid, body.answer, (body.comment or "").strip() or None, _photo(body.photo))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return services.track(gid)


@app.get("/api/public/stats")
def public_stats():
    """Aggregate operational counts only."""
    services.tick()
    return services.public_stats()


# ---------------- officer console (login required) ----------------
@app.get("/api/grievances")
def list_(status: str = None, category: str = None, priority: str = None, ward: str = None, q: str = None,
          limit: int = 200, stage: str = None, flagged: bool = False, department: str = None, no_work: bool = False,
          officer: dict = Officer):
    services.tick()
    return services.list_grievances(status, category, priority, ward, q, limit, stage, flagged, department, auth.scope(officer), no_work)


@app.get("/api/grievances/{gid}")
def get(gid: str, officer: dict = Officer):
    services.tick()
    g = _visible(gid, officer)
    # refresh similar cases and duplicates against the live index
    live = engine.analyze(g["text"], g["ward"], exclude_id=gid, point=services.point_of(g), category=g["category"])
    mine = {r["id"] for r in g["reports"]}  # reports already on this issue are not "duplicates" of it
    # a department head is shown matches from its own department only
    other = lambda s: s["id"] in mine or bool(auth.scope(officer) and CATEGORIES[s["category"]]["department"] != g["department"])
    g["live_similar"] = [s for s in live["similar_cases"] if not other(s)]
    g["live_duplicates"] = [s for s in live["possible_duplicates"] if not other(s)]
    return services.officer_view(g)


@app.get("/api/grievances/{gid}/photo")
def photo(gid: str, officer: dict = Officer):
    _visible(gid, officer)
    f = services.photo_file(gid)
    if not f:
        raise HTTPException(404, "No photo attached")
    return FileResponse(f[0], media_type=f[1], headers={"X-Content-Type-Options": "nosniff"})


@app.get("/api/grievances/{gid}/ground/{fid}/photo")
def ground_photo(gid: str, fid: int, officer: dict = Officer):
    g = _visible(gid, officer)
    f = services.ground_photo_file(g["master_id"], fid)
    if not f:
        raise HTTPException(404, "No photo attached")
    return FileResponse(f[0], media_type=f[1], headers={"X-Content-Type-Options": "nosniff"})


@app.patch("/api/grievances/{gid}")
def update(gid: str, body: UpdateIn, officer: dict = Officer):
    if body.status and body.status not in services.STATUSES:
        raise HTTPException(400, "Invalid status")
    if body.category and body.category not in CATEGORIES:
        raise HTTPException(400, "Invalid category")
    _visible(gid, officer)
    if body.master_id and body.master_id != gid:
        _visible(body.master_id, officer)  # can only link to an issue this officer can see
    g = services.update_grievance(gid, body.status, body.note, body.assigned_to, body.resolution_note,
                                  actor=officer["n"], category=body.category,
                                  resolution_photo=_photo(body.resolution_photo), master_id=body.master_id)
    if not g:
        raise HTTPException(404, "Grievance not found")
    return services.officer_view(g)


@app.post("/api/grievances/{gid}/draft")
def draft(gid: str, officer: dict = Officer):
    return llm.draft(_visible(gid, officer))


@app.get("/api/model", dependencies=[Officer])
def model_info():
    return {"verified_labels": services.verified_count(), "trained_on_verified": _metrics().get("verified_rows", 0)}


@app.post("/api/model/retrain")
def retrain(officer: dict = Officer):
    """Retrain on the synthetic templates + every officer-verified complaint, then hot-swap the model."""
    if auth.scope(officer):
        raise HTTPException(403, "Only the duty officer or a strike body can retrain the shared model")
    m = train.main()
    engine.load()
    return {k: m[k] for k in ("verified_rows", "holdout_accuracy", "holdout_size", "train_size", "test_size")}


# a department head's dashboards cover the issues in its own portal only
@app.get("/api/stats")
def stats(officer: dict = Officer):
    services.tick()
    return services.stats(auth.scope(officer))


@app.get("/api/analytics")
def analytics(officer: dict = Officer):
    return services.analytics(auth.scope(officer))


@app.get("/api/hotspots")
def hotspots(officer: dict = Officer):
    return services.hotspots(auth.scope(officer))


@app.get("/api/alerts")
def alerts(officer: dict = Officer):
    return services.alerts(auth.scope(officer))


# Serve built React app (single-command deployment)
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = (DIST / path).resolve()
        inside = f.is_relative_to(DIST.resolve())  # never serve files outside the build (../data/*.db)
        return FileResponse(f if path and inside and f.is_file() else DIST / "index.html")
