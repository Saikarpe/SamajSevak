import base64
import io
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth, llm, services
from app.main import app
from app.ml.engine import engine

# 1x1 PNG
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def picture(seed: int, size: int = 160, quality: int = 85) -> str:
    """A distinct test photo per seed; the same seed at another size / quality is 'visually similar'."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (160, 160), (seed * 37 % 255, seed * 91 % 255, seed * 53 % 255))
    d = ImageDraw.Draw(img)
    for i in range(6):
        x = (seed * (i + 3) * 29) % 120
        d.rectangle([x, (seed * (i + 5) * 17) % 120, x + 30 + 5 * i, 150], fill=((i * 40 + seed) % 255, (i * 70) % 255, 200 - i * 30))
    buf = io.BytesIO()
    img.resize((size, size)).save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def officer(client):
    token = client.post("/api/auth/login", json={"username": auth.DEMO_USER, "password": auth.DEMO_PASSWORD}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def citizen(client, name, phone):
    return {"X-Citizen-Token": client.post("/api/citizen/login", json={"name": name, "phone": phone}).json()["token"]}


def submit(client, text, headers=None, **kw):
    r = client.post("/api/grievances", json={"text": text, **kw}, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


def case(client, officer, gid):
    return client.get(f"/api/grievances/{gid}", headers=officer).json()


def notes(g):
    return " | ".join(e["note"] for e in g["timeline"])


# ---------------- existing pipeline (regression) ----------------
def test_critical_case_is_prioritised():
    a = engine.analyze("Live electric wire fallen near the school in Kothrud, children in danger, very dangerous!")
    assert a["category"] == "Electricity"
    assert a["priority_level"] in ("Critical", "High")
    assert a["ward"] == "Kothrud"
    assert a["recommendation"]["action_plan"]


def test_low_priority_case():
    a = engine.analyze("Illegal hoardings and banners near the park in Baner")
    assert a["category"] == "Encroachment"
    assert a["priority_level"] in ("Low", "Medium")


def test_hindi_and_marathi_get_the_full_pipeline():
    hi = engine.analyze("हडपसर में स्कूल के पास बिजली का तार टूटकर गिरा है, बच्चे रोज यहां से जाते हैं, बहुत खतरनाक है")
    assert (hi["language"]["code"], hi["category"], hi["ward"]) == ("hi", "Electricity", "Hadapsar")
    assert {"fallen wire", "dangerous"} <= set(hi["entities"]["urgency_terms"])
    assert "children" in hi["entities"]["vulnerable_groups"]
    assert hi["priority_level"] in ("Critical", "High") and not hi["needs_human_review"]
    mr = engine.analyze("कोथरूडमध्ये गेल्या 3 दिवसांपासून पाणी येत नाही, ज्येष्ठ नागरिकांना खूप त्रास होत आहे")
    assert (mr["language"]["code"], mr["category"], mr["ward"]) == ("mr", "Water Supply", "Kothrud")
    assert mr["entities"]["duration_days"] == 3 and "elderly" in mr["entities"]["vulnerable_groups"]


def test_other_languages_go_to_human_review():
    a = engine.analyze("எங்கள் பகுதியில் மூன்று நாட்களாக தண்ணீர் வரவில்லை")
    assert a["language"]["name"] == "Tamil" and a["needs_human_review"]


def test_officer_console_needs_login(client, officer):
    for path in ("/api/grievances", "/api/stats", "/api/analytics", "/api/hotspots", "/api/alerts", "/api/model"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=officer).status_code == 200
    assert client.patch("/api/grievances/SS-2026-00001", json={"status": "Resolved"}).status_code == 401
    assert client.get("/api/grievances", headers={"Authorization": "Bearer forged.token"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": auth.DEMO_USER, "password": "nope"}).status_code == 401
    # a citizen's token is not an officer's token
    token = citizen(client, "Meera Naik", "9000000001")["X-Citizen-Token"]
    assert client.get("/api/grievances", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_gps_decides_duplicates(client, officer):
    text = "Deep pothole on the road outside the bakery, bikes are skidding"
    spot = {"lat": 18.5300, "lng": 73.8500, "ward": "Shivajinagar"}
    first = submit(client, text, **spot)["id"]
    near = client.post("/api/analyze", json={"text": "Big pothole outside the bakery, two bikes skidded", **spot, "lat": 18.5303}).json()
    assert near["possible_duplicates"][0]["id"] == first and near["possible_duplicates"][0]["distance_m"] < 100
    # same words, same ward, 2 km away: a different pothole
    far = client.post("/api/analyze", json={"text": "Big pothole outside the bakery, two bikes skidded", **spot, "lat": 18.5480}).json()
    assert first not in [d["id"] for d in far["possible_duplicates"]]
    # a Marathi report of the same spot is matched across languages
    mr = client.post("/api/analyze", json={"text": "बेकरीसमोर रस्त्यावर मोठा खड्डा पडला आहे, दुचाकी घसरत आहेत", **spot}).json()
    assert first in [d["id"] for d in mr["possible_duplicates"]]
    # Hinglish shares no words with it and embeddings do not read it: location alone makes it a candidate
    hing = client.post("/api/analyze", json={"text": "Bakery ke saamne sadak par bada gadda hai, gaadi fisal rahi hai", **spot}).json()
    assert first in [d["id"] for d in hing["possible_duplicates"]]


def test_photo_evidence_and_category_correction(client, officer, monkeypatch):
    bad = client.post("/api/grievances", json={"text": "Street light not working near the temple", "photo": base64.b64encode(b"not an image").decode()})
    assert bad.status_code == 400
    gid = submit(client, "Street light not working near the temple in Aundh", photo=PNG)["id"]
    assert client.get(f"/api/grievances/{gid}/photo").status_code == 401
    assert client.get(f"/api/grievances/{gid}/photo", headers=officer).headers["content-type"] == "image/png"
    g = client.patch(f"/api/grievances/{gid}", json={"category": "Electricity"}, headers=officer).json()
    assert (g["category"], g["department"], g["label_source"]) == ("Electricity", "Electricity Board", "officer")
    assert (g["ai_category"], g["classification_source"]) == ("Street Lights", "OFFICER")  # the AI's answer is kept
    assert client.get("/api/model", headers=officer).json()["verified_labels"] >= 1
    # vision check: parsed from the model's JSON, and never raises
    monkeypatch.setattr(llm, "provider", lambda: "gemini")
    monkeypatch.setattr(llm, "_ask", lambda *a, **k: 'Sure: {"matches": true, "seen": "an unlit street lamp", "severity": "low"}')
    assert llm.check_photo(b"x", "image/png", g)["matches"] is True
    monkeypatch.setattr(llm, "_ask", lambda *a, **k: "no json here")
    assert "error" in llm.check_photo(b"x", "image/png", g)


# ---------------- citizen account and privacy ----------------
def test_citizen_account_and_privacy(client, officer):
    asha = citizen(client, "Asha Deshpande", "9812345678")
    assert client.post("/api/citizen/login", json={"name": "Someone Else", "phone": "9812345678"}).status_code == 400
    g = submit(client, "Garbage not collected near the market in Wakad for 5 days, stinking", asha)
    assert g["id"].startswith("SS-") and g["master_id"] == g["id"]
    mine = client.get("/api/citizen/grievances", headers=asha).json()
    assert [m["id"] for m in mine] == [g["id"]]
    assert client.get("/api/citizen/grievances").status_code == 401
    assert client.get("/api/citizen/grievances", headers=citizen(client, "Ravi Kale", "9811111111")).json() == []
    # the officer sees an internal citizen id, never the name or the phone; neither does the public page
    for body in (client.get("/api/grievances?limit=500", headers=officer).text, json.dumps(case(client, officer, g["id"])),
                 client.get(f"/api/track/{g['id']}").text, client.get("/api/public/stats").text,
                 client.get("/api/analytics", headers=officer).text):
        assert "9812345678" not in body and "Asha" not in body and "ip_hash" not in body and "testclient" not in body
    c = case(client, officer, g["id"])
    assert c["citizen_id"].startswith("CIT-") and not {"phone", "citizen_name", "photo_sha"} & set(c)
    pub = client.get(f"/api/track/{g['id']}").json()
    assert pub["status"] and not {"phone", "citizen_name", "citizen_id", "lat", "analysis", "review_signals"} & set(pub)


# ---------------- master issues ----------------
WIRE = {"lat": 18.5700, "lng": 73.7800}  # each scenario uses its own spot so they cannot match each other


def test_manual_join_then_ai_fallback(client, officer):
    a = submit(client, "Exposed live electric wire hanging from the pole near the bakery, sparks at night", citizen(client, "Anil Rao", "9000000011"), **WIRE)
    assert a["master_id"] == a["id"] and a["association_source"] is None
    # citizen B is shown the existing issue before submitting: safe fields only
    b_text = "There is a naked electrical wire hanging at the same place near the bakery"
    cards = client.post("/api/analyze", json={"text": b_text, **WIRE}).json()["existing_issues"]
    assert cards[0]["id"] == a["id"] and set(cards[0]) == {"id", "title", "category", "status", "stage", "ward", "created_at", "report_count", "distance_m"}
    b = submit(client, b_text, citizen(client, "Bina Shah", "9000000012"), join_issue=a["id"], **WIRE)
    assert (b["master_id"], b["association_source"]) == (a["id"], "CITIZEN")
    b_case = case(client, officer, b["id"])
    assert "Citizen joined existing issue" in notes(b_case) and "AI associated" not in notes(b_case)  # no AI merge after a manual join
    # citizen C finds nothing, submits in different words 40 m away: the AI links it afterwards
    c = submit(client, "Bijli ka khula taar latak raha hai bakery ke paas, dangerous electric wire with sparks", **{**WIRE, "lat": 18.57035})
    assert (c["master_id"], c["association_source"], c["report_count"]) == (a["id"], "AI", 3)
    master = case(client, officer, a["id"])
    assert [r["id"] for r in master["reports"]] == [a["id"], b["id"], c["id"]]  # one issue, three auditable reports
    assert master["reports"][1]["text"] == b_text and "m apart" in master["reports"][2]["association_note"]
    assert client.get(f"/api/track/{c['id']}").json()["text"].startswith("Bijli ka khula taar")  # original text kept
    queue = client.get("/api/grievances?limit=500", headers=officer).json()
    assert sum(g["id"] in (a["id"], b["id"], c["id"]) for g in queue) == 1  # one workload in the officer queue
    # the department's work on the master reaches every citizen on it
    client.patch(f"/api/grievances/{a['id']}", json={"status": "In Progress", "note": "Lineman sent"}, headers=officer)
    assert client.get(f"/api/track/{c['id']}").json()["status"] == "In Progress"
    # officer correction is audited: detach C as a separate issue, then link it back
    d = client.patch(f"/api/grievances/{c['id']}", json={"master_id": c["id"]}, headers=officer).json()
    assert d["master_id"] == c["id"] and "Detached from issue" in notes(d)
    d = client.patch(f"/api/grievances/{c['id']}", json={"master_id": a["id"]}, headers=officer).json()
    assert (d["master_id"], d["association_source"]) == (a["id"], "OFFICER")


def test_ai_does_not_merge_on_weak_evidence(client, officer):
    spot = {"lat": 18.5100, "lng": 73.9300, "ward": "Hadapsar"}
    a = submit(client, "Water pipeline burst outside the dairy, clean water flooding the lane", **spot)
    # same ward and category, same words, but 2 km away: a different pipe
    far = submit(client, "Water pipeline burst outside the dairy, clean water flooding the lane", **{**spot, "lat": 18.5290})
    assert far["master_id"] == far["id"]
    # same spot and department, different problem
    other = submit(client, "Wrong water bill received, the meter reading is incorrect", **spot)
    assert other["master_id"] == other["id"]
    # same ward, no GPS at all: similar words alone are not enough
    nogps = submit(client, "Water pipe has burst and water is flooding our lane in Hadapsar")
    assert nogps["master_id"] == nogps["id"]
    # the citizen was shown the issue and reported separately; with strong evidence the AI still links it, and says so
    again = submit(client, "Pipeline burst outside the dairy, water flooding the lane since morning", shown_issues=[a["id"]], **spot)
    assert (again["master_id"], again["association_source"]) == (a["id"], "AI")
    assert "shown before submission" in notes(case(client, officer, again["id"]))


def test_photo_reuse_is_evidence_not_proof(client, officer):
    spot = {"lat": 18.4600, "lng": 73.8700, "ward": "Katraj"}
    a = submit(client, "Huge garbage dump behind the temple, stinking and full of flies", photo=picture(1), **spot)
    # same photo, 150 m away, wording too different to match on text alone
    same = submit(client, "Kachre ka dher laga hai mandir ke peeche, badbu aa rahi hai", photo=picture(1), **{**spot, "lat": 18.4612})
    assert same["master_id"] == a["id"] and "same photo" in case(client, officer, same["id"])["association_note"]
    # the picture re-saved smaller by a messaging app still matches
    similar = submit(client, "Safai nahi ho rahi mandir ke peeche, gandagi bahut hai", photo=picture(1, size=96, quality=60), **{**spot, "lat": 18.4608})
    assert similar["master_id"] == a["id"] and "similar photo" in case(client, officer, similar["id"])["association_note"]
    # the same photo on an unrelated complaint across the city: not merged, not rejected, one signal only
    reused = submit(client, "Street light pole damaged near the bus depot in Kharadi", photo=picture(1), lat=18.5515, lng=73.9348)
    g = case(client, officer, reused["id"])
    assert reused["master_id"] == reused["id"] and g["status"] != "Rejected"
    assert any("already attached" in s for s in g["review_signals"])


def test_abuse_review_needs_two_signals(client, officer):
    spammer = citizen(client, "Test Spammer", "9000000099")
    text = "Illegal construction on public land near the lake, please stop it"
    first = submit(client, text, spammer, photo=picture(7), lat=18.5980, lng=73.7650)
    again = submit(client, text, spammer, photo=picture(7), lat=18.4580, lng=73.8680)  # same text and photo, other side of the city
    g = case(client, officer, again["id"])
    assert g["abuse_review"] == 1 and len(g["review_signals"]) >= 2 and g["status"] != "Rejected"
    assert "testclient" not in json.dumps(g) and "ip_hash" not in g  # the officer sees reasons, never the network
    assert first["id"] in [x["id"] for x in client.get("/api/grievances?limit=500", headers=officer).json()]
    assert again["id"] in [x["id"] for x in client.get("/api/grievances?flagged=true&limit=500", headers=officer).json()]


# ---------------- satisfaction ----------------
def test_citizen_verification(client, officer):
    spot = {"lat": 18.5020, "lng": 73.8640}
    lata, omar = citizen(client, "Lata More", "9000000021"), citizen(client, "Omar Khan", "9000000022")
    a = submit(client, "Sewage overflowing from the manhole in front of the clinic, foul smell", lata, **spot)
    b = submit(client, "Manhole in front of the clinic is overflowing with sewage water", omar, join_issue=a["id"], **spot)
    assert client.post(f"/api/grievances/{a['id']}/feedback", json={"satisfied": True}, headers=lata).status_code == 400  # not resolved yet
    client.patch(f"/api/grievances/{a['id']}", json={"status": "Resolved", "note": "Chamber cleared", "resolution_photo": PNG}, headers=officer)
    t = client.get(f"/api/track/{b['id']}").json()
    assert t["status"] == "Resolved" and t["satisfaction"] is None and t["resolution_photo"]  # awaiting confirmation
    services.run_escalations(datetime.now() + timedelta(days=400))
    assert client.get(f"/api/track/{a['id']}").json()["status"] == "Resolved"  # silence is never read as satisfied
    assert client.post(f"/api/grievances/{b['id']}/feedback", json={"satisfied": False}).status_code == 403  # only its own citizen
    assert client.post(f"/api/grievances/{b['id']}/feedback", json={"satisfied": False}, headers=lata).status_code == 403
    r = client.post(f"/api/grievances/{b['id']}/feedback", json={"satisfied": False, "rating": 1, "comment": "Still overflowing"}, headers=omar).json()
    assert (r["status"], r["satisfaction"], r["feedback_rating"]) == ("Not Satisfied", "Not Satisfied", 1)
    assert client.get(f"/api/track/{a['id']}").json()["status"] == "Not Satisfied"  # the whole issue is open again
    assert case(client, officer, a["id"])["id"] in [g["id"] for g in client.get("/api/grievances?status=Not Satisfied", headers=officer).json()]
    client.patch(f"/api/grievances/{a['id']}", json={"status": "Resolved", "note": "Line jetted again"}, headers=officer)
    assert client.get(f"/api/track/{b['id']}").json()["satisfaction"] is None  # everyone is asked again
    client.post(f"/api/grievances/{b['id']}/feedback", json={"satisfied": True, "rating": 4}, headers=omar)
    assert client.get(f"/api/track/{a['id']}").json()["status"] == "Closed"


# ---------------- escalation ----------------
def test_five_stage_escalation(client, officer):
    g = submit(client, "Dead animal lying on the road near the flyover for two days, terrible smell", lat=18.5310, lng=73.8480)
    gid = g["id"]
    seen = []
    for _ in range(6):
        c = case(client, officer, gid)
        seen.append((c["stage"], c["authority"]))
        if not c["stage_due"]:
            break
        services.run_escalations(datetime.strptime(c["stage_due"], services.FMT) + timedelta(seconds=1))
    dept = "Solid Waste Management"
    assert seen == [("Complaint", dept), ("Warning", dept),  # a warning never leaves the department
                    ("Strike 1", "Higher authority of the concerned department"), ("Strike 2", "Deputy Collector"),
                    ("Strike 3", "Final escalation body: IAS officers and opposition party leaders")]
    moves = [(e["prev_state"], e["new_state"], e["actor_type"]) for e in c["timeline"] if e["new_state"] in services.STAGES]
    assert moves == [("Complaint", "Warning", "System"), ("Warning", "Strike 1", "System"),
                     ("Strike 1", "Strike 2", "System"), ("Strike 2", "Strike 3", "System")]
    assert services.run_escalations(datetime.now() + timedelta(days=900)) == 0 or case(client, officer, gid)["stage"] == "Strike 3"
    # each stage lasts as configured: the full SLA, then half of it per later stage
    assert [services.stage_hours("Garbage & Sanitation", s) for s in services.STAGES] == [24, 12, 12, 12, None]
    assert client.get(f"/api/track/{gid}").json()["stage"] == "Strike 3"


def staff(client, username):
    r = client.post("/api/auth/login", json={"username": username, "password": auth.DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_department_heads_see_only_their_issues_until_escalated(client, officer):
    g = submit(client, "Sparks coming from the transformer near the vegetable market, power keeps tripping", lat=18.5150, lng=73.8560)
    dept = case(client, officer, g["id"])["department"]
    head = next(u for u, d in auth.DEPARTMENT_USERS.items() if d == dept)
    other = next(u for u, d in auth.DEPARTMENT_USERS.items() if d != dept)
    mine, theirs, strike = staff(client, head), staff(client, other), staff(client, "strike2")
    rows = client.get("/api/grievances", headers=mine).json()
    assert g["id"] in [r["id"] for r in rows]
    assert {r["department"] for r in rows} == {dept} and {r["stage"] for r in rows} <= set(services.HELD)
    assert g["id"] not in [r["id"] for r in client.get("/api/grievances", headers=theirs).json()]
    assert client.get(f"/api/grievances/{g['id']}", headers=theirs).status_code == 403
    assert client.patch(f"/api/grievances/{g['id']}", json={"note": "x"}, headers=theirs).status_code == 403
    assert client.post("/api/model/retrain", headers=mine).status_code == 403
    # strike bodies watch every department, at every stage
    assert len({r["department"] for r in client.get("/api/grievances?limit=500", headers=strike).json()}) > 1
    # still a Warning: stays with the department; after Strike 1 it leaves the department's portal
    services.run_escalations(datetime.strptime(case(client, officer, g["id"])["stage_due"], services.FMT) + timedelta(seconds=1))
    assert client.get(f"/api/grievances/{g['id']}", headers=mine).json()["stage"] == "Warning"
    services.run_escalations(datetime.strptime(case(client, officer, g["id"])["stage_due"], services.FMT) + timedelta(seconds=1))
    assert client.get(f"/api/grievances/{g['id']}", headers=mine).status_code == 403
    assert client.get(f"/api/grievances/{g['id']}", headers=strike).json()["stage"] == "Strike 1"
    assert client.get("/api/stats", headers=mine).json()["stages"].get("Strike 1", 0) == 0


def test_stage_reports_and_ground_feedback(client, officer):
    g = submit(client, "Huge pothole in the middle of the road near the old bridge, scooters are falling", lat=18.4710, lng=73.8650)
    gid = g["id"]
    cards = client.get(f"/api/track/{gid}").json()["stage_reports"]
    assert [c["stage"] for c in cards] == services.STAGES
    assert cards[0]["outcome"] == "in_progress" and cards[0]["due"] and {c["outcome"] for c in cards[1:]} == {"not_reached"}
    # the citizen says nothing is happening: shown on their card, flagged to the next authority, visible to officers
    t = client.post(f"/api/grievances/{gid}/ground", json={"answer": "no", "comment": "Nobody has come"}).json()
    assert t["stage_reports"][0]["mine"]["answer"] == "no" and t["stage_reports"][0]["ground"]["no"] == 1
    assert "Flagged to" in notes(t) and "Nobody has come" in notes(t)
    assert case(client, officer, gid)["ground_reports"][0]["answer"] == "no"
    assert gid in [r["id"] for r in client.get("/api/grievances?no_work=true&limit=500", headers=officer).json()]
    assert client.get("/api/stats", headers=officer).json()["no_work_reported"] >= 1
    # a new answer at the same stage replaces the old one
    client.post(f"/api/grievances/{gid}/ground", json={"answer": "partly"})
    assert [r["answer"] for r in case(client, officer, gid)["ground_reports"]] == ["partly"]
    # not resolved in time: the Complaint card says "not done", the Warning card is now in progress
    services.run_escalations(datetime.strptime(case(client, officer, gid)["stage_due"], services.FMT) + timedelta(seconds=1))
    cards = client.get(f"/api/track/{gid}").json()["stage_reports"]
    assert [c["outcome"] for c in cards[:3]] == ["not_done", "in_progress", "not_reached"] and cards[1]["mine"] is None
    # resolved: the card shows it waits for the citizen, and ground reports close in favour of the confirmation
    client.patch(f"/api/grievances/{gid}", json={"status": "Resolved", "note": "Pothole filled"}, headers=officer)
    t = client.get(f"/api/track/{gid}").json()
    assert t["stage_reports"][1]["outcome"] == "awaiting" and not t["can_report_ground"]
    assert client.post(f"/api/grievances/{gid}/ground", json={"answer": "yes"}).status_code == 400
    assert client.post(f"/api/grievances/{gid}/ground", json={"answer": "maybe"}).status_code == 422


def test_resolved_issues_do_not_escalate_and_rejection_keeps_the_record(client, officer):
    g = submit(client, "Bus stop shelter is broken near the stadium and people wait in the rain", lat=18.5200, lng=73.8200)
    client.patch(f"/api/grievances/{g['id']}", json={"status": "Resolved", "note": "Shelter repaired"}, headers=officer)
    services.run_escalations(datetime.now() + timedelta(days=400))
    assert case(client, officer, g["id"])["stage"] == "Complaint"
    r = submit(client, "Please ask my neighbour to return the ladder he borrowed last month", lat=18.5210, lng=73.8900)
    rejected = client.patch(f"/api/grievances/{r['id']}", json={"status": "Rejected", "note": "Private dispute, not a civic issue"}, headers=officer).json()
    assert rejected["status"] == "Rejected" and "Private dispute" in notes(rejected) and rejected["text"].startswith("Please ask")
    services.run_escalations(datetime.now() + timedelta(days=400))
    assert client.get(f"/api/track/{r['id']}").json()["stage"] == "Complaint"  # kept, auditable, not escalated


def test_citizen_category_choice_is_kept_beside_the_ai(client, officer):
    g = submit(client, "Street lights not working near the bus stop, the whole lane is dark", citizen_category="Safety & Law", lat=18.5600, lng=73.9100)
    c = case(client, officer, g["id"])
    assert (c["category"], c["ai_category"], c["citizen_category"], c["classification_source"]) == \
        ("Safety & Law", "Street Lights", "Safety & Law", "CITIZEN")
    assert c["status"] == "Submitted" and "disagree" in notes(c)  # an officer decides when they differ
    assert client.post("/api/grievances", json={"text": "Street lights not working here", "citizen_category": "Nonsense"}).status_code == 400


def test_dashboards(client, officer):
    s = client.get("/api/stats", headers=officer).json()
    assert set(s["stages"]) == set(services.STAGES) and s["multi_report_issues"] >= 3 and s["issues"] < s["total"]
    p = client.get("/api/public/stats").json()
    assert p["issues"] == s["issues"] and p["by_department"] and "by_ward" in p
    assert isinstance(client.get("/api/alerts", headers=officer).json(), list)
    assert client.post(f"/api/grievances/{client.get('/api/grievances?limit=1', headers=officer).json()[0]['id']}/draft", headers=officer).json()["text"]
