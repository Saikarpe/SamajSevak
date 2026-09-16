import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from app import db
from app.knowledge import CATEGORIES, WARDS
from app.ml.engine import engine

STATUSES = ["Submitted", "Assigned", "In Progress", "Resolved", "Rejected"]
FMT = "%Y-%m-%dT%H:%M:%S"


def now():
    return datetime.now().replace(microsecond=0)


def _next_id(c) -> str:
    n = c.execute("SELECT COUNT(*) FROM grievances").fetchone()[0] + 1
    return f"SS-{now().year}-{n:05d}"


def refresh_index():
    with db.conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id, title, text, category, ward, status, resolution_note, resolution_hours, created_at FROM grievances")]
    engine.build_index(rows)


def add_event(c, gid, status, note, actor="System", ts=None):
    c.execute("INSERT INTO events(grievance_id, ts, status, note, actor) VALUES (?,?,?,?,?)",
              (gid, (ts or now()).strftime(FMT), status, note, actor))


def create_grievance(text, ward=None, citizen_name=None, phone=None, channel="Web", created=None, reindex=True):
    a = engine.analyze(text, ward)
    ward = a["ward"]
    lat, lng = WARDS.get(ward, (18.52, 73.85))
    lat += random.uniform(-0.008, 0.008)
    lng += random.uniform(-0.008, 0.008)
    created = created or now()
    sla_due = created + timedelta(hours=a["recommendation"]["sla_hours"])
    dup = a["possible_duplicates"][0]["id"] if a["possible_duplicates"] else None
    status = "Assigned" if not a["needs_human_review"] else "Submitted"
    with db.conn() as c:
        gid = _next_id(c)
        c.execute(
            """INSERT INTO grievances(id, created_at, citizen_name, phone, channel, ward, lat, lng, text, title, category,
               confidence, department, priority_score, priority_level, sentiment, status, assigned_to, sla_due,
               duplicate_of, analysis) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gid, created.strftime(FMT), citizen_name, phone, channel, ward, lat, lng, text, a["title"], a["category"],
             a["confidence"], a["department"], a["priority_score"], a["priority_level"], a["sentiment"]["label"],
             status, a["department"] if status == "Assigned" else None, sla_due.strftime(FMT), dup, json.dumps(a)))
        add_event(c, gid, "Submitted", f"Grievance received via {channel}", "Citizen", created)
        if status == "Assigned":
            add_event(c, gid, "Assigned", f"AI auto-routed to {a['department']} ({a['priority_level']} priority, "
                                          f"{round(a['confidence'] * 100)}% confidence)", "SamajSevak AI", created)
        else:
            add_event(c, gid, "Submitted", "Low classification confidence — sent for human triage", "SamajSevak AI", created)
    if reindex:
        refresh_index()
    return get_grievance(gid)


def get_grievance(gid):
    with db.conn() as c:
        r = c.execute("SELECT * FROM grievances WHERE id=?", (gid,)).fetchone()
        if not r:
            return None
        g = db.row_to_dict(r)
        g["timeline"] = [dict(e) for e in c.execute("SELECT ts, status, note, actor FROM events WHERE grievance_id=? ORDER BY id", (gid,))]
    g["sla_breached"] = _breached(g)
    return g


def _breached(g):
    if not g.get("sla_due"):
        return False
    end = datetime.strptime(g["resolved_at"], FMT) if g.get("resolved_at") else now()
    return end > datetime.strptime(g["sla_due"], FMT)


def list_grievances(status=None, category=None, priority=None, ward=None, q=None, limit=200):
    sql, args = "SELECT * FROM grievances WHERE 1=1", []
    for col, val in (("status", status), ("category", category), ("priority_level", priority), ("ward", ward)):
        if val:
            sql += f" AND {col}=?"
            args.append(val)
    if q:
        sql += " AND (text LIKE ? OR id LIKE ? OR title LIKE ?)"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY CASE WHEN status IN ('Resolved','Rejected') THEN 1 ELSE 0 END, priority_score DESC, created_at DESC LIMIT ?"
    args.append(limit)
    with db.conn() as c:
        rows = [db.row_to_dict(r) for r in c.execute(sql, args)]
    for r in rows:
        r["sla_breached"] = _breached(r)
        r.pop("analysis", None)
    return rows


def update_grievance(gid, status=None, note=None, assigned_to=None, resolution_note=None, actor="Officer"):
    g = get_grievance(gid)
    if not g:
        return None
    sets, args = [], []
    if assigned_to:
        sets.append("assigned_to=?"); args.append(assigned_to)
    if status:
        sets.append("status=?"); args.append(status)
        if status == "Resolved":
            t = now()
            hrs = (t - datetime.strptime(g["created_at"], FMT)).total_seconds() / 3600
            sets += ["resolved_at=?", "resolution_hours=?", "resolution_note=?"]
            args += [t.strftime(FMT), round(hrs, 1), resolution_note or note or "Resolved"]
    with db.conn() as c:
        if sets:
            c.execute(f"UPDATE grievances SET {', '.join(sets)} WHERE id=?", (*args, gid))
        add_event(c, gid, status or g["status"], note or resolution_note or (f"Assigned to {assigned_to}" if assigned_to else "Updated"), actor)
    refresh_index()
    return get_grievance(gid)


def feedback(gid, rating):
    with db.conn() as c:
        c.execute("UPDATE grievances SET feedback_rating=? WHERE id=?", (rating, gid))
        add_event(c, gid, "Feedback", f"Citizen rated resolution {rating}/5", "Citizen")
    return get_grievance(gid)


# ---------------- analytics ----------------
def _all():
    with db.conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id, created_at, ward, category, department, priority_level, priority_score, status, sla_due, resolved_at, "
            "resolution_hours, sentiment, feedback_rating, lat, lng, title FROM grievances")]
    for r in rows:
        r["_created"] = datetime.strptime(r["created_at"], FMT)
        r["sla_breached"] = _breached(r)
    return rows


def stats():
    rows = _all()
    open_ = [r for r in rows if r["status"] not in ("Resolved", "Rejected")]
    resolved = [r for r in rows if r["status"] == "Resolved"]
    ratings = [r["feedback_rating"] for r in rows if r["feedback_rating"]]
    t = now()
    at_risk = [r for r in open_ if not r["sla_breached"] and datetime.strptime(r["sla_due"], FMT) - t < timedelta(hours=12)]
    return {
        "total": len(rows), "open": len(open_), "resolved": len(resolved),
        "critical_open": sum(1 for r in open_ if r["priority_level"] == "Critical"),
        "sla_breached_open": sum(1 for r in open_ if r["sla_breached"]),
        "sla_at_risk": len(at_risk),
        "sla_compliance": round(100 * sum(1 for r in resolved if not r["sla_breached"]) / max(1, len(resolved)), 1),
        "avg_resolution_hours": round(sum(r["resolution_hours"] or 0 for r in resolved) / max(1, len(resolved)), 1),
        "satisfaction": round(sum(ratings) / max(1, len(ratings)), 2),
        "last_7_days": sum(1 for r in rows if t - r["_created"] < timedelta(days=7)),
    }


def analytics():
    rows = _all()
    t = now()
    by_cat = Counter(r["category"] for r in rows)
    by_ward = Counter(r["ward"] for r in rows)
    by_pri = Counter(r["priority_level"] for r in rows if r["status"] not in ("Resolved", "Rejected"))
    by_sent = Counter(r["sentiment"] for r in rows)
    trend = []
    for d in range(29, -1, -1):
        day = (t - timedelta(days=d)).date()
        day_rows = [r for r in rows if r["_created"].date() == day]
        trend.append({"date": day.strftime("%d %b"), "received": len(day_rows),
                      "critical": sum(1 for r in day_rows if r["priority_level"] in ("Critical", "High"))})
    dept = defaultdict(lambda: {"total": 0, "resolved": 0, "hours": [], "on_time": 0, "open": 0})
    for r in rows:
        d = dept[r["department"]]
        d["total"] += 1
        if r["status"] == "Resolved":
            d["resolved"] += 1
            d["hours"].append(r["resolution_hours"] or 0)
            d["on_time"] += 0 if r["sla_breached"] else 1
        elif r["status"] != "Rejected":
            d["open"] += 1
    departments = [{"department": k, "total": v["total"], "open": v["open"], "resolved": v["resolved"],
                    "avg_hours": round(sum(v["hours"]) / max(1, len(v["hours"])), 1),
                    "sla_compliance": round(100 * v["on_time"] / max(1, v["resolved"]), 1)}
                   for k, v in dept.items()]
    departments.sort(key=lambda x: x["sla_compliance"])
    return {
        "by_category": [{"name": k, "value": v} for k, v in by_cat.most_common()],
        "by_ward": [{"name": k, "value": v} for k, v in by_ward.most_common()],
        "by_priority": [{"name": k, "value": by_pri.get(k, 0)} for k in ("Critical", "High", "Medium", "Low")],
        "by_sentiment": [{"name": k, "value": v} for k, v in by_sent.most_common()],
        "trend": trend,
        "departments": departments,
    }


def hotspots():
    rows = [r for r in _all() if r["status"] not in ("Resolved", "Rejected")]
    out = []
    for ward, (lat, lng) in WARDS.items():
        wr = [r for r in rows if r["ward"] == ward]
        if not wr:
            continue
        top = Counter(r["category"] for r in wr).most_common(1)[0]
        out.append({"ward": ward, "lat": lat, "lng": lng, "open": len(wr),
                    "critical": sum(1 for r in wr if r["priority_level"] in ("Critical", "High")),
                    "top_category": top[0], "top_count": top[1]})
    points = [{"id": r["id"], "lat": r["lat"], "lng": r["lng"], "priority": r["priority_level"],
               "category": r["category"], "title": r["title"]} for r in rows]
    return {"wards": sorted(out, key=lambda x: -x["open"]), "points": points}


def alerts():
    """Emerging-issue detection: compares last-7-day volume per (ward, category)
    against the trailing 3-week weekly baseline, plus SLA risk alerts."""
    rows = _all()
    t = now()
    recent, base = Counter(), Counter()
    for r in rows:
        age = (t - r["_created"]).days
        key = (r["ward"], r["category"])
        if age < 7:
            recent[key] += 1
        elif age < 28:
            base[key] += 1
    out = []
    for (ward, cat), n in recent.items():
        baseline = base[(ward, cat)] / 3
        ratio = n / max(baseline, 0.5)
        if n >= 4 and ratio >= 2:
            playbook = CATEGORIES[cat]["playbook"]
            out.append({
                "type": "Emerging hotspot", "severity": "Critical" if ratio >= 4 else "High",
                "ward": ward, "category": cat, "count_7d": n, "baseline_weekly": round(baseline, 1),
                "spike_ratio": round(ratio, 1),
                "message": f"{n} {cat.lower()} complaints in {ward} this week — {round(ratio, 1)}x the usual rate. Likely a systemic root cause.",
                "recommendation": f"Launch a ward-level drive instead of case-by-case fixes: {playbook[-1].lower()}; {playbook[0].lower()}.",
            })
    breached = [r for r in rows if r["status"] not in ("Resolved", "Rejected") and r["sla_breached"]]
    by_dept = Counter(r["department"] for r in breached)
    for dept, n in by_dept.most_common(3):
        if n >= 3:
            out.append({"type": "SLA breach", "severity": "High", "department": dept, "count": n,
                        "message": f"{n} open grievances have crossed SLA in {dept}.",
                        "recommendation": "Re-allocate field staff and send escalation to the head of department."})
    return sorted(out, key=lambda a: (a["severity"] != "Critical", -a.get("count_7d", a.get("count", 0))))


# ---------------- seeding ----------------
def seed_if_empty():
    with db.conn() as c:
        if c.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]:
            refresh_index()
            return
    from app.ml.dataset import generate_history
    rng = random.Random(3)
    random.seed(3)
    names = ["Amit Patil", "Sneha Kulkarni", "Rahul Deshmukh", "Priya Joshi", "Imran Shaikh", "Kavita More",
             "Suresh Jadhav", "Anjali Pawar", "Rohan Gaikwad", "Fatima Khan", "Vikram Shinde", "Pooja Bhosale"]
    hist = generate_history()
    hist.sort(key=lambda h: h.get("recent", False))
    t = now()
    for h in hist:
        age_h = rng.uniform(1, 6 * 24) if h.get("recent") else 1 + 88 * 24 * rng.random() ** 1.5
        created = t - timedelta(hours=age_h)
        channel = rng.choices(["Web", "WhatsApp", "Call Centre", "Mobile App", "Twitter/X"], [35, 25, 15, 20, 5])[0]
        g = create_grievance(h["text"], h["ward"], rng.choice(names), f"98{rng.randint(10000000, 99999999)}",
                             channel, created, reindex=False)
        sla = CATEGORIES[g["category"]]["sla_hours"]
        res_h = sla * rng.lognormvariate(-0.35, 0.55)
        with db.conn() as c:
            if not h.get("recent") and age_h > res_h * 1.3 and rng.random() < 0.95:
                resolved_at = created + timedelta(hours=res_h)
                c.execute("UPDATE grievances SET status='Resolved', resolved_at=?, resolution_hours=?, resolution_note=?, "
                          "feedback_rating=?, assigned_to=department WHERE id=?",
                          (resolved_at.strftime(FMT), round(res_h, 1), h["resolution"],
                           rng.choices([5, 4, 3, 2, 1], [35, 35, 18, 8, 4])[0], g["id"]))
                add_event(c, g["id"], "In Progress", "Field team dispatched", "Field Officer", created + timedelta(hours=res_h * 0.3))
                add_event(c, g["id"], "Resolved", h["resolution"], "Field Officer", resolved_at)
            elif rng.random() < 0.6:
                c.execute("UPDATE grievances SET status='In Progress' WHERE id=?", (g["id"],))
                add_event(c, g["id"], "In Progress", "Field team dispatched", "Field Officer", created + timedelta(hours=min(age_h, 3)))
    refresh_index()
