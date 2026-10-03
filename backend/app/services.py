import base64
import binascii
import hashlib
import hmac
import io
import json
import os
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from app import auth, db, geo, lang, llm
from app.knowledge import CATEGORIES, DEPARTMENT_LEVEL, ESCALATION_STAGES, WARDS
from app.ml.engine import engine

# Resolved = fixed by the department, awaiting the citizen's confirmation. Closed = citizen satisfied.
# Not Satisfied = citizen rejected the resolution; the issue is open again and escalation continues.
STATUSES = ["Submitted", "Assigned", "In Progress", "Resolved", "Not Satisfied", "Closed", "Rejected"]
DONE = ("Resolved", "Closed")
CLOSED = DONE + ("Rejected",)
STAGES = [s[0] for s in ESCALATION_STAGES]
# stages where the issue is held by its own department (Complaint, Warning); the strikes go upward
HELD = tuple(s[0] for s in ESCALATION_STAGES if s[1] == DEPARTMENT_LEVEL)
DEPT_QUEUE_TARGET = 7  # demo seed: open issues each department head starts with
FMT = "%Y-%m-%dT%H:%M:%S"
PHOTO_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
MAX_PHOTO_BYTES = 3 * 1024 * 1024
PHASH_NEAR = 6  # perceptual hashes within this many bits (of 64) count as the same picture
# abuse signals: thresholds and how long the salted network hash is kept
BURST_REPORTS, BURST_MINUTES, IP_RETENTION_DAYS = 5, 60, 30
# what a citizen sees with only a tracking ID: no name, phone, coordinates or AI internals
TRACK_FIELDS = ("id", "created_at", "status", "text", "title", "category", "department", "ward", "priority_level",
                "sla_due", "sla_breached", "resolved_at", "resolution_note", "feedback_rating", "feedback_text",
                "satisfaction", "language", "photo", "resolution_photo", "timeline", "master_id",
                "association_source", "report_count", "stage", "stage_due", "authority")
# never sent to the officer console: who the citizen is, and raw abuse-signal inputs
PRIVATE_FIELDS = ("citizen_name", "phone", "ip_hash", "photo_sha", "photo_phash")
# the issue's operational state, copied from the master onto every report linked to it
SYNCED = ("status", "assigned_to", "category", "department", "sla_due", "resolved_at", "resolution_note",
          "resolution_hours", "resolution_photo", "stage", "stage_due")


def now():
    return datetime.now().replace(microsecond=0)


def _next_id(c) -> str:
    """Highest number used this year + 1 (not a row count, so a deleted row never causes a clash)."""
    prefix = f"SS-{now().year}-"
    last = c.execute("SELECT MAX(CAST(SUBSTR(id, ?) AS INTEGER)) FROM grievances WHERE id LIKE ?",
                     (len(prefix) + 1, prefix + "%")).fetchone()[0]
    return f"{prefix}{(last or 0) + 1:05d}"


def refresh_index():
    with db.conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id, title, text, category, ward, status, resolution_note, resolution_hours, created_at, "
            "lat, lng, geo_source, master_id FROM grievances")]
    engine.build_index(rows)


# ---------------- photos ----------------
def decode_photo(data: str) -> tuple[bytes, str]:
    """Validate an uploaded image (base64 or data URL) -> (bytes, extension). Raises ValueError."""
    try:
        raw = base64.b64decode(data.split(",", 1)[-1], validate=True)
    except binascii.Error:
        raise ValueError("Photo is not valid base64")
    ext = ("jpg" if raw[:3] == b"\xff\xd8\xff" else "png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else
           "webp" if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP" else None)
    if not ext:
        raise ValueError("Photo must be a JPEG, PNG or WebP image")
    if len(raw) > MAX_PHOTO_BYTES:
        raise ValueError("Photo is larger than 3 MB")
    return raw, ext


def photo_hashes(raw: bytes) -> tuple[str, str | None]:
    """(SHA-256, 64-bit difference hash). The first matches byte-identical files, the second survives
    resizing and re-compression. Neither understands what the picture shows."""
    sha = hashlib.sha256(raw).hexdigest()
    try:
        from PIL import Image
        px = Image.open(io.BytesIO(raw)).convert("L").resize((9, 8)).tobytes()
        bits = "".join("1" if px[r * 9 + col] > px[r * 9 + col + 1] else "0" for r in range(8) for col in range(8))
        return sha, f"{int(bits, 2):016x}"
    except Exception:  # Pillow missing or unreadable image: exact matching still works
        return sha, None


def _image_matches(c, hashes, exclude_id=None):
    """Earlier reports carrying the same or a visually similar photo -> {report id: (label, master id)}."""
    out = {}
    if hashes:
        for r in c.execute("SELECT id, master_id, photo_sha, photo_phash FROM grievances WHERE photo_sha IS NOT NULL"):
            if r["id"] == exclude_id:
                continue
            if r["photo_sha"] == hashes[0]:
                out[r["id"]] = ("same photo", r["master_id"])
            elif hashes[1] and r["photo_phash"] and bin(int(hashes[1], 16) ^ int(r["photo_phash"], 16)).count("1") <= PHASH_NEAR:
                out[r["id"]] = ("visually similar photo", r["master_id"])
    return out


def _save_photo(name: str, photo: tuple[bytes, str]) -> str:
    db.UPLOADS.mkdir(parents=True, exist_ok=True)
    filename = f"{name}.{photo[1]}"
    (db.UPLOADS / filename).write_bytes(photo[0])
    return filename


def photo_file(gid, kind="photo"):
    """(path, media type) of the citizen's evidence photo or the officer's resolution proof."""
    with db.conn() as c:
        r = c.execute(f"SELECT {'resolution_photo' if kind == 'resolution' else 'photo'} FROM grievances WHERE id=?", (gid,)).fetchone()
    path = db.UPLOADS / r[0] if r and r[0] else None
    return (path, PHOTO_TYPES[path.suffix[1:]]) if path and path.is_file() else None


def check_photo(gid):
    """Background step after submission: optional vision-LLM check of the evidence photo."""
    g, f = get_grievance(gid), photo_file(gid)
    result = llm.check_photo(f[0].read_bytes(), f[1], g) if g and f else None
    if result:
        with db.conn() as c:
            c.execute("UPDATE grievances SET photo_check=? WHERE id=?", (json.dumps(result), gid))


def point_of(g):
    return (g["lat"], g["lng"]) if g.get("geo_source") in geo.PRECISE else None


# ---------------- audit trail ----------------
def add_event(c, gid, status, note, actor="System", ts=None, prev=None, new=None):
    """prev / new record a state change (status, escalation stage or association)."""
    actor_type = {"Citizen": "Citizen", "SamajSevak AI": "AI", "System": "System"}.get(actor, "Officer")
    c.execute("INSERT INTO events(grievance_id, ts, status, note, actor, actor_type, prev_state, new_state) VALUES (?,?,?,?,?,?,?,?)",
              (gid, (ts or now()).strftime(FMT), status, note, actor, actor_type, prev, new))


# ---------------- citizens ----------------
def citizen_login(name: str, phone: str, strict: bool = True):
    """Name + phone is the citizen's login. Officers only ever see the internal citizen id.
    strict=False (name/phone typed on an anonymous submission) returns None instead of raising."""
    name, digits = " ".join((name or "").split()), re.sub(r"\D", "", phone or "")[-10:]
    if len(name) < 2 or len(digits) != 10:
        if strict:
            raise ValueError("Enter your name and a 10-digit mobile number")
        return None
    with db.conn() as c:
        row = c.execute("SELECT * FROM citizens WHERE phone=?", (digits,)).fetchone()
        if row and row["name"].lower() != name.lower():
            if strict:
                raise ValueError("This mobile number is registered with a different name")
            return None
        if not row:
            cid = f"CIT-{c.execute('SELECT COUNT(*) FROM citizens').fetchone()[0] + 1:05d}"
            c.execute("INSERT INTO citizens(id, name, phone, created_at) VALUES (?,?,?,?)", (cid, name, digits, now().strftime(FMT)))
            row = {"id": cid, "name": name}
    return {"id": row["id"], "name": row["name"], "token": auth.issue({"c": row["id"], "n": row["name"]}, hours=24 * 30)}


def citizen_grievances(cid):
    with db.conn() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM grievances WHERE citizen_id=? ORDER BY created_at DESC", (cid,))]
    return [{k: v for k, v in track(i).items() if k != "timeline"} for i in ids]


# ---------------- master issues ----------------
def stage_hours(category, stage):
    """How long an issue may stay in `stage` before it escalates (None for the last stage)."""
    i = STAGES.index(stage)
    fixed = [float(x) for x in os.getenv("SAMAJSEVAK_STAGE_HOURS", "").split(",") if x.strip()]
    if ESCALATION_STAGES[i][2] is None:
        return None
    return fixed[i] if len(fixed) == len(STAGES) - 1 else CATEGORIES[category]["sla_hours"] * ESCALATION_STAGES[i][2]


def authority(stage, department):
    """Who holds the issue at this stage. Complaint and Warning never leave the department."""
    who = ESCALATION_STAGES[STAGES.index(stage or "Complaint")][1]
    return department if who == DEPARTMENT_LEVEL else who


def _sync(c, master_id):
    """Copy the master issue's operational state onto every report linked to it."""
    cols = ", ".join(f"{k}=(SELECT m.{k} FROM grievances m WHERE m.id=?)" for k in SYNCED)
    c.execute(f"UPDATE grievances SET {cols} WHERE master_id=? AND id<>?", (*[master_id] * len(SYNCED), master_id, master_id))


def find_master(c, text, a, point, hashes):
    """AI fallback after a report is submitted without joining an issue: does it describe an issue that
    is already open? Returns (master id, evidence) only on a combination of signals, never on ward,
    category or a keyword alone:
      both have GPS      within 300 m and wording matches, or within 300 m and the photo matches
      a side has no GPS  same ward and (wording matches strongly and same landmark, or photo and wording match)
    """
    images = {}
    for label, master in _image_matches(c, hashes).values():
        images.setdefault(master, label)
    for s in engine.open_matches(text, a["category"], a["ward"], point):
        master, d, wording = s["master_id"], s["distance_m"], s["text_similarity"]
        photo = images.get(master)
        if d is not None:
            strong = d <= 300 and (wording >= 0.45 or (d <= 100 and wording >= 0.35) or photo)
        else:
            landmark = a["entities"]["landmark"]
            strong = (wording >= 0.6 and landmark and landmark == engine.entities(s["text"])["landmark"]) \
                or (photo and wording >= 0.35)
        if strong:
            evidence = [f"{d} m apart" if d is not None else f"same ward ({a['ward']}), same landmark" if not photo else f"same ward ({a['ward']})",
                        f"{round(wording * 100)}% wording match", f"same category ({a['category']})"] + ([photo] if photo else [])
            return master, evidence
    # the wording did not match at all (another language, say) but the photo is one already on an open
    # issue of the same category at the same place
    for master, photo in images.items():
        m = c.execute("SELECT category, status, ward, lat, lng, geo_source FROM grievances WHERE id=?", (master,)).fetchone()
        if m["category"] != a["category"] or m["status"] in CLOSED:
            continue
        d = round(geo.haversine_m(*point, m["lat"], m["lng"])) if point and m["geo_source"] in geo.PRECISE else None
        if d <= 300 if d is not None else m["ward"] == a["ward"]:
            return master, [f"{d} m apart" if d is not None else f"same ward ({a['ward']})", photo, f"same category ({a['category']})"]
    return None


def issue_cards(text, category, ward, point):
    """Open issues a citizen may be about to report again. Public-safe fields only."""
    seen, cards = set(), []
    with db.conn() as c:
        for s in engine.open_matches(text, category, ward, point):
            if s["master_id"] in seen:
                continue
            seen.add(s["master_id"])
            m = c.execute("SELECT id, title, category, status, stage, ward, created_at, (SELECT COUNT(*) FROM grievances r "
                          "WHERE r.master_id=g.id) AS report_count FROM grievances g WHERE id=?", (s["master_id"],)).fetchone()
            cards.append({**dict(m), "distance_m": s["distance_m"]})
    return cards[:3]


def _abuse_signals(c, citizen_id, ip_hash, text, hashes, master_id, exclude_id=None):
    """Reasons a person should look at this report. Signals only: nothing is rejected automatically,
    and the review flag needs two of them (one shared network or one reused photo proves nothing)."""
    signals = []
    for rid, (label, master) in _image_matches(c, hashes, exclude_id).items():
        if master != master_id:  # the same photo on the same issue is ordinary supporting evidence
            signals.append(f"{label.capitalize()} already attached to {rid}, a different issue")
            break
    who, args = [], []
    if citizen_id:
        who.append("citizen_id=?"); args.append(citizen_id)
    if ip_hash:
        who.append("ip_hash=?"); args.append(ip_hash)
    if who:
        since = (now() - timedelta(minutes=BURST_MINUTES)).strftime(FMT)
        n = c.execute(f"SELECT COUNT(*) FROM grievances WHERE ({' OR '.join(who)}) AND created_at>=?", (*args, since)).fetchone()[0]
        if n >= BURST_REPORTS:
            signals.append(f"{n + 1} reports from this account or network in {BURST_MINUTES} minutes")
        day = (now() - timedelta(hours=24)).strftime(FMT)
        same = c.execute(f"SELECT COUNT(*) FROM grievances WHERE ({' OR '.join(who)}) AND created_at>=? AND text=?", (*args, day, text)).fetchone()[0]
        if same:
            signals.append(f"Identical text submitted {same + 1} times in 24 hours by this account or network")
    return signals


def hash_ip(ip):
    """Salted, one-way. Lets two reports be recognised as coming from one network without storing the address."""
    return hmac.new(auth.SECRET, ip.encode(), hashlib.sha256).hexdigest()[:24] if ip else None


def create_grievance(text, ward=None, citizen_name=None, phone=None, channel="Web", created=None, reindex=True,
                     point=None, geo_source="gps", photo=None, citizen_id=None, citizen_category=None,
                     join_issue=None, shown_issues=(), ip=None):
    """One citizen report. It either joins an existing master issue or becomes a new one.

    point: (lat, lng) from the citizen's GPS or map pin. photo: (bytes, extension) from decode_photo.
    join_issue: master issue the citizen chose to join; when given, the AI association is skipped.
    shown_issues: issues that were suggested and that the citizen did not join (audit only)."""
    ai = engine.classify(text, lang.detect(text))[0]
    a = engine.analyze(text, ward, point=point, category=citizen_category)
    conflict = bool(citizen_category) and citizen_category != ai["category"] and ai["confidence"] >= 0.40
    a.update(ai_category=ai["category"], ai_confidence=ai["confidence"], citizen_category=citizen_category,
             classification_source="CITIZEN" if citizen_category else "AI", confidence=ai["confidence"],
             needs_human_review=a["needs_human_review"] or conflict)
    ward = a["ward"]
    if point:
        lat, lng = point
    else:  # no location shared: ward centre, jittered so pins do not stack (approximate)
        geo_source = "ward"
        lat, lng = WARDS.get(ward, (18.52, 73.85))
        lat += random.uniform(-0.008, 0.008)
        lng += random.uniform(-0.008, 0.008)
    seeding = created is not None
    created = created or now()
    sla_due = created + timedelta(hours=a["recommendation"]["sla_hours"])
    dup = a["possible_duplicates"][0]["id"] if a["possible_duplicates"] else None
    status = "Assigned" if not a["needs_human_review"] else "Submitted"
    hashes = photo_hashes(photo[0]) if photo else None
    if not citizen_id and citizen_name and phone:  # name + phone typed on the form is the citizen's account
        citizen_id = (citizen_login(citizen_name, phone, strict=False) or {}).get("id")
    with db.conn() as c:
        gid = _next_id(c)
        master, source, evidence = gid, None, None
        joined = join_issue and c.execute("SELECT id FROM grievances WHERE id=? AND master_id=id AND status NOT IN (?,?,?)",
                                          (join_issue, *CLOSED)).fetchone()
        if joined:  # the citizen said "this is the same issue": no AI decision is made for this report
            master, source = join_issue, "CITIZEN"
        else:
            found = find_master(c, text, a, point, hashes)
            if found:
                master, source, evidence = found[0], "AI", found[1]
        signals = [] if seeding else _abuse_signals(c, citizen_id, hash_ip(ip), text, hashes, master)
        c.execute(
            """INSERT INTO grievances(id, created_at, channel, ward, lat, lng, text, title, category,
               confidence, department, priority_score, priority_level, sentiment, status, assigned_to, sla_due,
               duplicate_of, analysis, geo_source, language, photo, master_id, association_source, association_note,
               citizen_id, ai_category, citizen_category, classification_source, stage, stage_due, photo_sha,
               photo_phash, ip_hash, review_signals, abuse_review)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gid, created.strftime(FMT), channel, ward, lat, lng, text, a["title"], a["category"],
             a["confidence"], a["department"], a["priority_score"], a["priority_level"], a["sentiment"]["label"],
             status, a["department"] if status == "Assigned" else None, sla_due.strftime(FMT), dup, json.dumps(a),
             geo_source, a["language"]["name"], _save_photo(gid, photo) if photo else None, master, source,
             "; ".join(evidence) if evidence else None, citizen_id, ai["category"], citizen_category,
             a["classification_source"], STAGES[0], sla_due.strftime(FMT), *(hashes or (None, None)),
             None if seeding else hash_ip(ip), json.dumps(signals) if signals else None, int(len(signals) >= 2)))
        add_event(c, gid, "Submitted", f"Grievance received via {channel}" + (" with photo evidence" if photo else ""),
                  "Citizen", created)
        if citizen_category:
            add_event(c, gid, "Submitted", f"Citizen selected category: {citizen_category}" + (
                f" (AI suggested {ai['category']}, {round(ai['confidence'] * 100)}% — officer to review)" if conflict else ""),
                "Citizen", created)
        if shown_issues and not joined:
            add_event(c, gid, "Submitted", f"Existing issue(s) shown before submission: {', '.join(shown_issues)} — citizen reported separately",
                      "Citizen", created)
        if master != gid:
            n = c.execute("SELECT COUNT(*) FROM grievances WHERE master_id=?", (master,)).fetchone()[0]
            if source == "CITIZEN":
                add_event(c, gid, "Submitted", f"Citizen joined existing issue {master}", "Citizen", created, new=master)
            else:
                add_event(c, gid, "Submitted", f"AI associated this report with existing issue {master}: {'; '.join(evidence)}",
                          "SamajSevak AI", created, new=master)
            add_event(c, master, "Report added", f"Supporting report {gid} linked ({'joined by citizen' if source == 'CITIZEN' else 'matched by AI'}); "
                                                 f"{n} reports on this issue", "Citizen" if source == "CITIZEN" else "SamajSevak AI", created)
            # more people reporting never lowers urgency
            c.execute("UPDATE grievances SET priority_score=?, priority_level=? WHERE id=? AND priority_score<?",
                      (a["priority_score"], a["priority_level"], master, a["priority_score"]))
            _sync(c, master)
        elif status == "Assigned":
            add_event(c, gid, "Assigned", f"AI auto-routed to {a['department']} ({a['priority_level']} priority, "
                                          f"{round(a['confidence'] * 100)}% confidence)", "SamajSevak AI", created)
        else:
            why = ("Citizen and AI disagree on the category" if conflict else
                   "Low classification confidence" if a["language"]["support"] == "full" else
                   f"{a['language']['name']} complaint: category suggested, risk keywords not read")
            add_event(c, gid, "Submitted", f"{why} — sent for human triage", "SamajSevak AI", created)
    if reindex:
        refresh_index()
    return get_grievance(gid)


def _flags(g):
    """Computed fields; photo columns hold file names, the API only says whether one exists."""
    g["sla_breached"] = _breached(g)
    g["photo"], g["resolution_photo"] = bool(g.get("photo")), bool(g.get("resolution_photo"))
    g["authority"] = authority(g.get("stage"), g.get("department"))
    return g


def get_grievance(gid):
    """One report with its master issue's state. A master also lists every report linked to it."""
    with db.conn() as c:
        r = c.execute("SELECT * FROM grievances WHERE id=?", (gid,)).fetchone()
        if not r:
            return None
        g = db.row_to_dict(r)
        master = g["master_id"] or gid
        # a linked report shows its own intake events plus what happened to the master issue
        # (officer work, escalations, and every change of state)
        g["timeline"] = [dict(e) for e in c.execute(
            "SELECT ts, status, note, actor, actor_type, prev_state, new_state FROM events WHERE grievance_id=? "
            "OR (grievance_id=? AND ?<>? AND (actor_type IN ('Officer','System') OR prev_state IS NOT NULL)) ORDER BY ts, id",
            (gid, master, gid, master))]
        g["reports"] = [dict(x) for x in c.execute(
            "SELECT id, created_at, text, title, channel, language, association_source, association_note, citizen_id, "
            "satisfaction, feedback_rating, feedback_text, photo IS NOT NULL AS photo, geo_source, lat, lng, abuse_review "
            "FROM grievances WHERE master_id=? ORDER BY created_at, id", (master,))]
        g["report_count"] = len(g["reports"])
        g["ground_reports"] = _ground_rows(c, master)
    return _flags(g)


def officer_view(g):
    """Strip everything that identifies the citizen: the console shows the internal citizen id only."""
    return g and {k: v for k, v in g.items() if k not in PRIVATE_FIELDS}


def track(gid):
    """Public status view for a tracking ID."""
    g = get_grievance(gid)
    return g and {**{k: g[k] for k in TRACK_FIELDS}, "sla_hours": CATEGORIES[g["category"]]["sla_hours"],
                  "stages": STAGES, "has_account": bool(g["citizen_id"]),
                  "stage_reports": stage_reports(g["master_id"], own_id=g["id"]),
                  "can_report_ground": g["status"] not in CLOSED and g["status"] != "Resolved"}


def _breached(g):
    if not g.get("sla_due"):
        return False
    end = datetime.strptime(g["resolved_at"], FMT) if g.get("resolved_at") else now()
    return end > datetime.strptime(g["sla_due"], FMT)


def visible(g, scope):
    """Can this officer see the issue? A department head (scope = its department) only sees its own
    department's issues while they are at a department-level stage; strike bodies and admins see all."""
    return bool(g) and (not scope or (g["department"] == scope and (g["stage"] or STAGES[0]) in HELD))


def list_grievances(status=None, category=None, priority=None, ward=None, q=None, limit=200, stage=None, flagged=None,
                    department=None, scope=None, no_work=None):
    """The officer queue: one row per master issue, however many citizens reported it."""
    sql = ("SELECT g.*, (SELECT COUNT(*) FROM grievances r WHERE r.master_id=g.id) AS report_count, "
           "(SELECT MAX(r.abuse_review) FROM grievances r WHERE r.master_id=g.id) AS any_abuse_review, "
           "(SELECT COUNT(*) FROM ground_reports x WHERE x.master_id=g.id AND x.stage=g.stage AND x.answer='no') AS ground_no, "
           "(SELECT COUNT(*) FROM ground_reports x WHERE x.master_id=g.id AND x.stage=g.stage AND x.answer<>'no') AS ground_yes "
           "FROM grievances g WHERE g.master_id=g.id")
    args = []
    for col, val in (("status", status), ("category", category), ("priority_level", priority), ("ward", ward), ("stage", stage),
                     ("department", scope or department)):
        if val:
            sql += f" AND g.{col}=?"
            args.append(val)
    if scope:
        sql += f" AND COALESCE(g.stage, '{STAGES[0]}') IN ({','.join('?' * len(HELD))})"
        args += HELD
    if flagged:
        sql += " AND EXISTS (SELECT 1 FROM grievances r WHERE r.master_id=g.id AND r.abuse_review=1)"
    if no_work:  # open issues where a citizen says nothing is happening at the current stage
        sql += (" AND g.status NOT IN ('Resolved','Closed','Rejected') AND EXISTS "
                "(SELECT 1 FROM ground_reports x WHERE x.master_id=g.id AND x.stage=g.stage AND x.answer='no')")
    if q:  # a match in any linked report finds its issue
        sql += " AND g.id IN (SELECT master_id FROM grievances WHERE text LIKE ? OR id LIKE ? OR title LIKE ?)"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY CASE WHEN g.status IN ('Resolved','Closed','Rejected') THEN 1 ELSE 0 END, g.priority_score DESC, g.created_at DESC LIMIT ?"
    args.append(limit)
    with db.conn() as c:
        rows = [db.row_to_dict(r) for r in c.execute(sql, args)]
    for r in rows:
        _flags(r)
        r.pop("analysis", None)
    return [officer_view(r) for r in rows]


def update_grievance(gid, status=None, note=None, assigned_to=None, resolution_note=None, actor="Officer",
                     category=None, resolution_photo=None, master_id=None):
    """Officer action. Work happens on the master issue, so an action on a linked report is applied to
    its master. master_id links this report to another issue (or, given its own id, detaches it)."""
    g = get_grievance(gid)
    if not g:
        return None
    if master_id:
        return _associate(g, master_id, actor)
    report_id, gid = gid, g["master_id"]
    if gid != report_id:
        g = get_grievance(gid)
    sets, args, relabel = [], [], None
    if category:
        # officer confirms or corrects the category: re-triage, and keep it as a training label
        a = engine.analyze(g["text"], g["ward"], exclude_id=gid, point=point_of(g), category=category)
        a.update(ai_category=g["ai_category"], citizen_category=g["citizen_category"], classification_source="OFFICER")
        due = datetime.strptime(g["created_at"], FMT) + timedelta(hours=a["recommendation"]["sla_hours"])
        sets += ["category=?", "confidence=?", "department=?", "priority_score=?", "priority_level=?", "sla_due=?",
                 "analysis=?", "label_source='officer'", "classification_source='OFFICER'"]
        args += [category, 1.0, a["department"], a["priority_score"], a["priority_level"], due.strftime(FMT), json.dumps(a)]
        if g["stage"] == STAGES[0]:  # the first deadline follows the corrected category's SLA
            sets.append("stage_due=?"); args.append(due.strftime(FMT))
        if g["assigned_to"] in (None, g["department"]) and not assigned_to:  # still with the auto-routed department
            sets.append("assigned_to=?"); args.append(a["department"])
        relabel = (f"Category confirmed by officer: {category}" if category == g["category"] else
                   f"Category corrected by officer: {g['category']} → {category}, re-routed to {a['department']}")
        if g["status"] == "Submitted" and not status:  # human triage done
            status = "Assigned"
    if resolution_photo:
        sets.append("resolution_photo=?"); args.append(_save_photo(f"{gid}-resolved", resolution_photo))
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
        if status == "Resolved":  # every citizen on the issue is asked again; earlier answers do not carry over
            c.execute("UPDATE grievances SET satisfaction=NULL WHERE master_id=?", (gid,))
        change = (g["status"], status) if status and status != g["status"] else (None, None)
        if relabel:
            add_event(c, gid, status or g["status"], relabel, actor, prev=g["category"], new=category)
        if note or resolution_note or assigned_to or resolution_photo or not relabel:
            text = note or resolution_note or (f"Assigned to {assigned_to}" if assigned_to else "Updated")
            if status == "Resolved":
                text += " — awaiting citizen confirmation"
            add_event(c, gid, status or g["status"], text + (" (photo proof attached)" if resolution_photo else ""), actor,
                      prev=change[0], new=change[1])
        _sync(c, gid)
    refresh_index()
    return get_grievance(report_id)


def _associate(g, target_id, actor):
    """Officer links a report to another issue, confirms an existing link, or detaches it."""
    gid = g["id"]
    target = get_grievance(target_id)
    if not target:
        return None
    with db.conn() as c:
        if target_id == gid:  # detach: the report becomes its own issue, keeping its current state
            if g["master_id"] != gid:
                c.execute("UPDATE grievances SET master_id=id, association_source=NULL, association_note=NULL WHERE id=?", (gid,))
                add_event(c, gid, g["status"], f"Detached from issue {g['master_id']} by officer: a separate issue", actor,
                          prev=g["master_id"], new=gid)
                add_event(c, g["master_id"], g["status"], f"Report {gid} detached by officer", actor)
        else:
            master = target["master_id"]
            confirm = g["master_id"] == master and gid != master
            # a master moves together with the reports already linked to it
            c.execute("UPDATE grievances SET master_id=?, association_source='OFFICER' WHERE id=? OR (master_id=? AND ?<>?)",
                      (master, gid, gid, gid, master))
            add_event(c, gid, g["status"], f"Association with issue {master} {'confirmed' if confirm else 'made'} by officer", actor,
                      prev=g["master_id"], new=master)
            if not confirm:
                add_event(c, master, target["status"], f"Report {gid} linked by officer", actor)
            _sync(c, master)
    refresh_index()
    return get_grievance(gid)


def verified_count():
    with db.conn() as c:
        return c.execute("SELECT COUNT(*) FROM grievances WHERE label_source='officer'").fetchone()[0]


def feedback(gid, rating=None, satisfied=None, comment=None):
    """The citizen's verdict on their own report once the issue is marked resolved.
    Not satisfied reopens the whole issue; saying nothing is never read as satisfied."""
    g = get_grievance(gid)
    master = g["master_id"]
    with db.conn() as c:
        if rating is not None or comment:
            c.execute("UPDATE grievances SET feedback_rating=COALESCE(?, feedback_rating), feedback_text=COALESCE(?, feedback_text) WHERE id=?",
                      (rating, comment, gid))
            if rating is not None:
                add_event(c, gid, "Feedback", f"Citizen rated resolution {rating}/5", "Citizen")
        if satisfied is not None:
            c.execute("UPDATE grievances SET satisfaction=? WHERE id=?", ("Satisfied" if satisfied else "Not Satisfied", gid))
            unhappy = c.execute("SELECT COUNT(*) FROM grievances WHERE master_id=? AND satisfaction='Not Satisfied'", (master,)).fetchone()[0]
            if not satisfied:
                c.execute("UPDATE grievances SET status='Not Satisfied', resolved_at=NULL WHERE id=?", (master,))
                # the comment itself stays on the report (officers see it); the shared timeline only says what happened
                add_event(c, master, "Not Satisfied", f"Citizen ({gid}) is not satisfied with the resolution — issue reopened, "
                                                      "escalation continues", "Citizen", prev=g["status"], new="Not Satisfied")
            elif not unhappy:
                c.execute("UPDATE grievances SET status='Closed' WHERE id=?", (master,))
                add_event(c, master, "Closed", f"Citizen ({gid}) confirmed the issue is resolved", "Citizen", prev=g["status"], new="Closed")
            else:
                add_event(c, master, g["status"], f"Citizen ({gid}) is satisfied; another citizen on this issue is not, so it stays open", "Citizen")
            _sync(c, master)
    if satisfied is False:
        run_escalations()  # the stage clock was paused while it waited for confirmation
    refresh_index()
    return get_grievance(gid)


# ---------------- ground reports: the citizen's view of the work at each stage ----------------
GROUND = {"yes": "work is happening", "partly": "some work, not enough", "no": "no work on the ground"}


def ground_report(gid, answer, comment=None, photo=None):
    """The citizen answers "is work happening on the ground?" for the stage the issue is at now.
    One answer per report and stage (a new answer replaces it). A "no" is flagged to the next authority."""
    g = get_grievance(gid)
    master, stage = g["master_id"], g["stage"] or STAGES[0]
    i = STAGES.index(stage)
    if g["status"] in CLOSED or g["status"] == "Resolved":
        raise ValueError("This issue is resolved or closed: use the confirmation instead")
    name = _save_photo(f"{gid}-ground-{i}", photo) if photo else None
    nxt = authority(STAGES[i + 1], g["department"]) if i + 1 < len(STAGES) else None
    note = f"Citizen ({gid}) at the {stage} stage: {GROUND[answer]}" + (f" \u2014 \u201c{comment}\u201d" if comment else "")
    if answer == "no" and nxt:
        note += f". Flagged to {nxt} ahead of the deadline"
    note += " (photo attached)" if photo else ""
    with db.conn() as c:
        c.execute("DELETE FROM ground_reports WHERE grievance_id=? AND stage=?", (gid, stage))
        c.execute("INSERT INTO ground_reports(grievance_id, master_id, stage, answer, comment, photo, created_at) VALUES (?,?,?,?,?,?,?)",
                  (gid, master, stage, answer, comment, name, now().strftime(FMT)))
        add_event(c, master, g["status"], note, "Citizen")
        if master != gid:  # the citizen also sees it on their own report
            add_event(c, gid, g["status"], note, "Citizen")
    return get_grievance(gid)


def _ground_rows(c, master):
    return [dict(r) for r in c.execute(
        "SELECT id, grievance_id, stage, answer, comment, photo IS NOT NULL AS photo, created_at FROM ground_reports "
        "WHERE master_id=? ORDER BY created_at, id", (master,))]


def ground_photo_file(gid, fid):
    with db.conn() as c:
        r = c.execute("SELECT photo FROM ground_reports WHERE id=? AND master_id=?", (fid, gid)).fetchone()
    path = db.UPLOADS / r[0] if r and r[0] else None
    return (path, PHOTO_TYPES[path.suffix[1:]]) if path and path.is_file() else None


def stage_reports(master_id, own_id=None):
    """One report card per escalation stage of the issue: who held it, for how long, what officers did,
    and whether the work was done there (resolved) or not (escalated). Citizens see the counts of
    everyone's ground reports but only their own wording (own_id)."""
    m = get_grievance(master_id)
    with db.conn() as c:
        ground = _ground_rows(c, master_id)
    moves = {e["new_state"]: e["ts"] for e in m["timeline"] if e["actor_type"] == "System" and e["new_state"] in STAGES}
    at = STAGES.index(m["stage"] or STAGES[0])
    cards, t = [], now().strftime(FMT)
    for i, stage in enumerate(STAGES):
        card = {"stage": stage, "holder": authority(stage, m["department"])}
        if i > at:
            cards.append({**card, "outcome": "not_reached"})
            continue
        start = m["created_at"] if i == 0 else moves.get(stage, m["created_at"])
        end = moves.get(STAGES[i + 1]) if i < at else None
        if end:
            outcome = "not_done"
        elif m["status"] == "Closed":
            outcome, end = "done", m["resolved_at"]
        elif m["status"] == "Resolved":
            outcome, end = "awaiting", m["resolved_at"]
        elif m["status"] == "Rejected":
            outcome = "rejected"
        else:
            outcome = "in_progress"
        actions = [e for e in m["timeline"] if e["actor_type"] == "Officer" and start <= e["ts"] <= (end or t)]
        mine = [r for r in ground if r["stage"] == stage and r["grievance_id"] == own_id]
        cards.append({**card, "outcome": outcome, "start": start, "end": end,
                      "due": m["stage_due"] if outcome == "in_progress" else None,
                      "hours": max(0.0, round((datetime.strptime(end or t, FMT) - datetime.strptime(start, FMT)).total_seconds() / 3600, 1)),
                      "actions": len(actions), "last_action": actions[-1]["note"] if actions else None,
                      "ground": {a: sum(1 for r in ground if r["stage"] == stage and r["answer"] == a) for a in GROUND},
                      "mine": {k: mine[-1][k] for k in ("answer", "comment", "created_at")} if mine else None})
    return cards


# ---------------- escalation ----------------
def run_escalations(at=None):
    """Move every unresolved master issue whose stage deadline has passed to the next stage.
    Complaint -> Warning (still the department) -> Strike 1 -> Strike 2 -> Strike 3. Returns how many moved.
    An issue awaiting citizen confirmation (Resolved) is not escalated; Not Satisfied puts it back in."""
    at = at or now()
    moved = 0
    with db.conn() as c:
        due = c.execute("SELECT id, category, department, stage, stage_due FROM grievances WHERE master_id=id AND stage<>? "
                        "AND stage_due IS NOT NULL AND stage_due<=? AND status NOT IN (?,?,?)",
                        (STAGES[-1], at.strftime(FMT), *CLOSED)).fetchall()
        for r in due:
            stage, when = r["stage"], datetime.strptime(r["stage_due"], FMT)
            while stage != STAGES[-1] and when <= at:  # an issue left alone for long passes through every stage in order
                nxt = STAGES[STAGES.index(stage) + 1]
                holder = authority(nxt, r["department"])
                note = (f"Not resolved within the {stage} period. Warning issued: the issue stays with {holder}" if nxt == "Warning"
                        else f"Not resolved within the {stage} period. Escalated to {nxt}: {holder}")
                add_event(c, r["id"], nxt, note, "System", when, prev=stage, new=nxt)
                hours = stage_hours(r["category"], nxt)
                stage, when = nxt, when + timedelta(hours=hours) if hours else when
                moved += 1
            c.execute("UPDATE grievances SET stage=?, stage_due=? WHERE id=?",
                      (stage, None if stage == STAGES[-1] else when.strftime(FMT), r["id"]))
            _sync(c, r["id"])
    return moved


_last_tick = None


def tick():
    """Cheap, lazy scheduler: escalations are brought up to date at most once a minute, whenever someone looks."""
    global _last_tick
    if _last_tick is None or now() - _last_tick >= timedelta(seconds=60):
        _last_tick = now()
        run_escalations()


def purge_ip_hashes():
    with db.conn() as c:
        c.execute("UPDATE grievances SET ip_hash=NULL WHERE ip_hash IS NOT NULL AND created_at<?",
                  ((now() - timedelta(days=IP_RETENTION_DAYS)).strftime(FMT),))


# ---------------- analytics ----------------
def _all(scope=None):
    """Every report; for a department head only its department's issues at the department-level stages."""
    with db.conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id, created_at, ward, category, department, priority_level, priority_score, status, sla_due, resolved_at, "
            "resolution_hours, sentiment, feedback_rating, lat, lng, title, master_id, stage, satisfaction, abuse_review, "
            "duplicate_of FROM grievances")]
    rows = [r for r in rows if visible(r, scope)]
    for r in rows:
        r["_created"] = datetime.strptime(r["created_at"], FMT)
        r["sla_breached"] = _breached(r)
    return rows


def stats(scope=None):
    """Counts are citizen reports unless the name says 'issues' (master issues, the unit of work)."""
    rows = _all(scope)
    open_ = [r for r in rows if r["status"] not in CLOSED]
    resolved = [r for r in rows if r["status"] in DONE]
    ratings = [r["feedback_rating"] for r in rows if r["feedback_rating"]]
    masters = [r for r in rows if r["master_id"] == r["id"]]
    open_issues = [r for r in masters if r["status"] not in CLOSED]
    per_issue = Counter(r["master_id"] for r in rows)
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
        "issues": len(masters), "open_issues": len(open_issues),
        "stages": {s: sum(1 for r in open_issues if r["stage"] == s) for s in STAGES},
        "awaiting_confirmation": sum(1 for r in masters if r["status"] == "Resolved"),
        "not_satisfied": sum(1 for r in masters if r["status"] == "Not Satisfied"),
        "closed": sum(1 for r in masters if r["status"] == "Closed"),
        "rejected": sum(1 for r in masters if r["status"] == "Rejected"),
        "multi_report_issues": sum(1 for n in per_issue.values() if n > 1),
        "linked_reports": sum(n - 1 for n in per_issue.values()),
        "duplicate_candidates": sum(1 for r in open_issues if r["duplicate_of"]),
        "abuse_review": sum(1 for r in rows if r["abuse_review"]),
        "no_work_reported": _no_work_count({r["id"] for r in open_issues}),
    }


def _no_work_count(ids):
    """Open issues where a citizen reports no work at the issue's current stage."""
    with db.conn() as c:
        hit = {r[0] for r in c.execute("SELECT DISTINCT x.master_id FROM ground_reports x JOIN grievances g ON g.id=x.master_id "
                                       "WHERE x.answer='no' AND x.stage=g.stage")}
    return len(hit & ids)


def public_stats():
    """Aggregate, factual counts for the public page. No complaint text, people or exact locations."""
    s, rows = stats(), _all()
    masters = [r for r in rows if r["master_id"] == r["id"]]
    table = lambda key: [{"name": k, "received": sum(1 for r in masters if r[key] == k),
                          "resolved": sum(1 for r in masters if r[key] == k and r["status"] in DONE),
                          "pending": sum(1 for r in masters if r[key] == k and r["status"] not in CLOSED)}
                         for k in sorted({r[key] for r in masters if r[key]})]
    return {"reports_received": s["total"], "issues": s["issues"], "issues_resolved": s["awaiting_confirmation"] + s["closed"],
            "issues_confirmed_by_citizens": s["closed"], "issues_pending": s["open_issues"], "not_satisfied": s["not_satisfied"],
            "stages": s["stages"], "multi_report_issues": s["multi_report_issues"], "linked_reports": s["linked_reports"],
            "avg_resolution_hours": s["avg_resolution_hours"], "by_department": table("department"), "by_ward": table("ward")}


def analytics(scope=None):
    rows = _all(scope)
    t = now()
    by_cat = Counter(r["category"] for r in rows)
    by_ward = Counter(r["ward"] for r in rows)
    by_pri = Counter(r["priority_level"] for r in rows if r["status"] not in CLOSED)
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
        if r["status"] in DONE:
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


def hotspots(scope=None):
    rows = [r for r in _all(scope) if r["status"] not in CLOSED]
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


def alerts(scope=None):
    """Emerging-issue detection: compares last-7-day volume per (ward, category)
    against the trailing 3-week weekly baseline, plus SLA risk alerts."""
    rows = _all(scope)
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
    breached = [r for r in rows if r["master_id"] == r["id"] and r["status"] not in CLOSED and r["sla_breached"]]
    by_dept = Counter(r["department"] for r in breached)
    for dept, n in by_dept.most_common(3):
        if n >= 3:
            out.append({"type": "SLA breach", "severity": "High", "department": dept, "count": n,
                        "message": f"{n} open issues have crossed SLA in {dept}.",
                        "recommendation": "Re-allocate field staff; see the escalation stage on each issue."})
    return sorted(out, key=lambda a: (a["severity"] != "Critical", -a.get("count_7d", a.get("count", 0))))


# ---------------- seeding ----------------
def seed_if_empty():
    with db.conn() as c:
        if c.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]:
            refresh_index()
            return
    from app.ml.dataset import LANDMARKS, generate_history
    rng = random.Random(3)
    geo_rng = random.Random(5)
    random.seed(3)
    names = ["Amit Patil", "Sneha Kulkarni", "Rahul Deshmukh", "Priya Joshi", "Imran Shaikh", "Kavita More",
             "Suresh Jadhav", "Anjali Pawar", "Rohan Gaikwad", "Fatima Khan", "Vikram Shinde", "Pooja Bhosale"]
    citizens = [citizen_login(n, f"98{rng.randint(10000000, 99999999)}")["id"] for n in names]
    hist = generate_history()
    hist.sort(key=lambda h: h.get("recent", False))
    t = now()
    indexed = False
    for h in hist:
        age_h = rng.uniform(1, 6 * 24) if h.get("recent") else 1 + 88 * 24 * rng.random() ** 1.5
        created = t - timedelta(hours=age_h)
        channel = rng.choices(["Web", "WhatsApp", "Call Centre", "Mobile App", "Twitter/X"], [35, 25, 15, 20, 5])[0]
        # simulated GPS: every complaint about the same landmark in a ward lands within ~50 m of the same spot
        spot = h.get("spot") or next((s for s in LANDMARKS if s.lower() in h["text"].lower()), None)
        base = random.Random(f"{h['ward']}|{spot}") if spot else geo_rng
        lat, lng = WARDS[h["ward"]]
        point = (lat + base.uniform(-0.008, 0.008) + geo_rng.uniform(-0.0003, 0.0003),
                 lng + base.uniform(-0.008, 0.008) + geo_rng.uniform(-0.0003, 0.0003))
        if h.get("recent") and not indexed:  # recent reports are matched against open issues, like live ones
            refresh_index()
            indexed = True
        g = create_grievance(h["text"], h["ward"], channel=channel, created=created, reindex=bool(h.get("recent")),
                             point=point, geo_source="seed", citizen_id=rng.choice(citizens))
        if g["master_id"] != g["id"]:  # joined an existing issue: its state is the master's
            continue
        sla = CATEGORIES[g["category"]]["sla_hours"]
        res_h = sla * rng.lognormvariate(-0.35, 0.55)
        with db.conn() as c:
            if not h.get("recent") and age_h > res_h * 1.3 and rng.random() < 0.95:
                resolved_at = created + timedelta(hours=res_h)
                # most citizens confirmed; the rest never answered, so those stay "awaiting confirmation"
                rating = rng.choices([5, 4, 3, 2, 1], [35, 35, 18, 8, 4])[0] if rng.random() < 0.85 else None
                c.execute("UPDATE grievances SET status=?, resolved_at=?, resolution_hours=?, resolution_note=?, "
                          "feedback_rating=?, satisfaction=?, assigned_to=department WHERE id=?",
                          ("Closed" if rating else "Resolved", resolved_at.strftime(FMT), round(res_h, 1), h["resolution"],
                           rating, "Satisfied" if rating else None, g["id"]))
                add_event(c, g["id"], "In Progress", "Field team dispatched", "Field Officer", created + timedelta(hours=res_h * 0.3))
                add_event(c, g["id"], "Resolved", h["resolution"] + " — awaiting citizen confirmation", "Field Officer", resolved_at)
                if rating:
                    add_event(c, g["id"], "Closed", "Citizen confirmed the issue is resolved", "Citizen",
                              resolved_at + timedelta(hours=rng.uniform(1, 30)), prev="Resolved", new="Closed")
            elif rng.random() < 0.6:
                c.execute("UPDATE grievances SET status='In Progress' WHERE id=?", (g["id"],))
                add_event(c, g["id"], "In Progress", "Field team dispatched", "Field Officer", created + timedelta(hours=min(age_h, 3)))
                _sync(c, g["id"])
    run_escalations()
    _top_up_departments(rng, geo_rng, citizens)
    run_escalations()
    refresh_index()


def _top_up_departments(rng, geo_rng, citizens, target=DEPT_QUEUE_TARGET):
    """Demo data: every department head's portal starts with `target` open issues at the Complaint /
    Warning stage. Each one is a normal report filed some time within those two periods; a report the
    AI routes elsewhere or joins to an existing issue simply stays as it is."""
    from app.ml.dataset import complaint_text
    held = ",".join("?" * len(HELD))
    for cat, info in CATEGORIES.items():
        for _ in range(4 * target):
            with db.conn() as c:
                n = c.execute(f"SELECT COUNT(*) FROM grievances WHERE master_id=id AND department=? AND status NOT IN (?,?,?) "
                              f"AND stage IN ({held})", (info["department"], *CLOSED, *HELD)).fetchone()[0]
            if n >= target:
                break
            ward = rng.choice(list(WARDS))
            lat, lng = WARDS[ward]
            point = (lat + geo_rng.uniform(-0.008, 0.008), lng + geo_rng.uniform(-0.008, 0.008))
            # Complaint lasts the SLA and Warning half of it: anywhere up to 1.25 x SLA is still with the department
            created = now() - timedelta(hours=info["sla_hours"] * rng.uniform(0.1, 1.25))
            create_grievance(complaint_text(cat, rng, ward), ward, channel=rng.choice(["Web", "WhatsApp", "Mobile App", "Call Centre"]),
                             created=created, reindex=False, point=point, geo_source="seed", citizen_id=rng.choice(citizens))
