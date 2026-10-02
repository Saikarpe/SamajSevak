# SamajSevak — How It Works (Input → Output, Step by Step)

A plain-language walkthrough of what happens to one citizen complaint, from the moment
it is typed to the moment an officer sees a ranked, explained, actionable case.
Every step names the exact file and function that does the work.

---

## 0. The one-sentence version

> A citizen types a complaint in free text → the backend runs 8 small AI/NLP steps on it →
> out comes a **category, department, priority score with reasons, duplicates, an action plan
> and an ETA** → it is saved in SQLite → dashboards, maps and spike alerts are computed from
> everything saved so far.

There is **no single big model**. It is a pipeline of small, cheap, explainable pieces.
Everything runs offline on a laptop. An LLM is optional and only used for writing replies.

---

## 1. The moving parts

| Part | Where | Job |
|---|---|---|
| React UI | `frontend/src/` | Citizen form + officer console (7 pages) |
| FastAPI | `backend/app/main.py` | ~14 REST endpoints, also serves the built React app |
| AI engine | `backend/app/ml/engine.py` | The whole analysis pipeline (one class, `Engine`) |
| Knowledge base | `backend/app/knowledge.py` | 11 categories → department, SLA, severity, playbook; wards; keyword weights |
| Classifier | `backend/models/classifier.joblib` | TF-IDF + Logistic Regression, trained by `ml/train.py` |
| Synthetic data | `backend/app/ml/dataset.py` | Generates training rows + ~450 historical cases |
| Database | SQLite via `backend/app/db.py` | 2 tables: `grievances`, `events` |
| Services | `backend/app/services.py` | Save, update, analytics, hotspots, spike alerts, seeding |
| LLM (optional) | `backend/app/llm.py` | Gemini / OpenAI draft reply; falls back to a template |

---

## 2. Before anyone types anything — startup

When you run `uvicorn app.main:app`, three things happen in order
(`main.py` `lifespan` → `db.init()` → `services.seed_if_empty()`):

1. **Tables created** — `db.py:SCHEMA` runs `CREATE TABLE IF NOT EXISTS`.
2. **Model loaded** — `Engine.__init__` (`ml/engine.py:35`) loads `classifier.joblib`.
   If the file is missing it **trains itself on the spot** by calling `train.main()`.
3. **Database seeded (first run only)** — `services.seed_if_empty` (`services.py:253`)
   generates ~450 fake-but-realistic past grievances, spreads them over the last 90 days,
   marks most of them resolved with a resolution note, and deliberately plants an
   **emerging hotspot** (18 extra drainage/health cases in Hadapsar this week) so the alert
   engine has something real to find in a demo.
4. **Similarity index built** — `services.refresh_index` (`services.py:23`) pulls every row
   and calls `engine.build_index()`, which fits a fresh TF-IDF matrix over all complaint texts.
   This index is what makes "similar past cases" and duplicate detection possible.
   It is rebuilt every time a grievance is created or updated.

> **Why synthetic data?** The recommender learns "what actually fixed this before" by
> retrieving past resolved cases. With an empty database it would have nothing to retrieve,
> so the demo would look empty. In production this seed is replaced by real history.

---

## 3. The input

The citizen types on `/citizen` (`frontend/src/pages/Submit.jsx`):

```
"Live electric wire has fallen near the primary school in Kothrud since yesterday.
 Children walk here daily, extremely dangerous!"
```

Optional extras: ward (or "auto-detect from text"), channel (Web / WhatsApp / Call Centre /
Mobile App / Twitter), name, phone. There is also a **Speak** button — it uses the browser's
built-in `SpeechRecognition` (`en-IN`), no server-side speech model.

**Behind the scenes while typing:** a 500 ms debounce timer
(`Submit.jsx` `useEffect`) fires `POST /api/analyze` once the text passes 15 characters.
That endpoint runs the *full* pipeline but **saves nothing** — that is how the live
preview panel on the right can show department/priority/ETA before submitting.

---

## 4. The pipeline — 8 steps inside `Engine.analyze()`

`ml/engine.py:195`. This single function is the heart of the project.
Everything below happens in a few milliseconds, in this order.

### Step 1 — Clean the text (`core_text`, `engine.py:26`)
A regex strips ~15 boilerplate phrases: *"Respected sir,"*, *"Please do the needful."*,
*"Nobody is responding to our calls."*, etc.

**Why:** these phrases appear in almost every complaint, so they make two unrelated
complaints look similar to a TF-IDF model. Removing them makes similarity focus on the
actual issue. Note: cleaning is used for **similarity**, while the **classifier** sees the
raw text (it was trained on text that included these openers, so it is already robust to them).

### Step 2 — Classify & route (`classify`, `engine.py:69`)
```
raw text → TF-IDF word 1–2 grams  ┐
        → TF-IDF char 3–5 grams   ┘ (FeatureUnion) → Logistic Regression → 11 probabilities
```
- **Two vectorizers on purpose.** Word n-grams catch phrases ("live wire", "no water").
  Character n-grams (`char_wb`, 3–5) catch **misspellings and Hinglish** — "bijli", "kachra",
  "pani nahi aa raha", "sadak" — because they match on letter patterns, not dictionary words.
- **Logistic Regression** with `class_weight="balanced"`, `C=4.0`. Chosen over a neural net
  because it is instant, tiny, trains in seconds, and gives calibrated probabilities you can
  show to an officer.
- Output: top-3 categories with confidence. `category` = top-1.
- **Confidence gate:** if top-1 confidence < **0.40**, `needs_human_review = true`. That case
  is *not* auto-assigned — it goes to a human triage queue instead. This is the honesty valve.
- The category is then looked up in `knowledge.py:CATEGORIES` to get the **department**,
  **SLA hours** and **severity weight**. Routing is a dictionary lookup, not a second model —
  deliberately, because departmental ownership is policy, not something to guess.

*Measured accuracy* (`backend/models/metrics.json`): 100% on the synthetic test split
(3520 train / 880 test), 99.2% on 121 hand-written development complaints (optimistic: the
templates were written with these in view), and **81.8% (54/66)** on a final hand-written set
(`ml/evalset.py:FINAL`) that was written only after the templates and settings were frozen.
On that final set 49 complaints passed the 0.40 gate and 6 of them were routed wrongly.

### Step 3 — Entity extraction (`entities`, `engine.py:96`)
Pure regex + dictionary lookups, no NER model:
- **ward** — first ward name from `knowledge.py:WARDS` found in the text.
- **duration_days** — matches `"3 days"`, `"since one week"`, `"last month"`, `"yesterday"`
  and normalises everything to days (week ×7, month ×30).
- **landmark** — a preposition pattern: `near|opposite|behind|next to|outside|in front of …`.
- **urgency_terms** — hits against ~50 weighted risk keywords (`live wire` 1.0, `dengue` 0.9,
  `urgent` 0.6…). A small trick: substring hits are de-duplicated so `"danger"` is dropped
  when `"dangerous"` already matched.
- **vulnerable_groups** — children, elderly, pregnant, hospital, patients, women, disabled.

**Why regex and not spaCy/BERT?** The entities here are a closed, known set (12 wards,
fixed risk vocabulary). A closed set is exactly where rules beat a model: zero latency,
zero training data, and the officer can see the matched word.

### Step 4 — Sentiment & distress (`sentiment`, `engine.py:77`)
Lexicon scoring, not a model:
- Count negative words (`NEGATIVE_WORDS`) and positive words, each negative word ×1.5 if
  preceded by an **intensifier** ("very", "extremely", "totally").
- Add penalties for `!` count and for ALL-CAPS words — because shouting is a real signal.
- `score` ∈ [-1, 1] → label Negative / Neutral / Positive.
- `distress` ∈ [0, 1] → emotion Anger/Frustration (≥0.5) / Concern (>0.1) / Calm.

Distress is not decoration — it feeds the priority score in Step 6, so an angry repeat
complainant genuinely gets moved up.

### Step 5 — Duplicate & cluster detection (`similar`, `engine.py:50`)
1. Vectorize the cleaned text with the **index built at startup**.
2. `cosine_similarity` against every stored complaint.
3. **Category-aware re-ranking:** same-category rows get `+0.10`, different-category rows get
   `×0.6`. This is the fix for a classic TF-IDF failure — two complaints sharing only the words
   "near the school in Kothrud" would otherwise look similar.
4. Keep the top-k above a **0.12** floor.

Then in `analyze`:
- `same_area_open` = similar **and** same ward **and** same category **and** not resolved
  **and** similarity ≥ **0.25** → this is the **cluster size**.
- `possible_duplicates` = same set but similarity ≥ **0.55** → shown to the officer, and the
  first one is stored in the `duplicate_of` column.

**Why two thresholds:** 0.55 means "probably the same incident, don't send two crews";
0.25 means "different people reporting the same underlying problem, so it's more urgent".
Same measurement, two different decisions.

### Step 6 — Explainable priority score (`priority`, `engine.py:121`)
Additive, capped at 100. **Every component is returned as a `{factor, points}` row**, which is
what the UI renders as "why this priority":

| Factor | Points |
|---|---|
| Category severity | `severity × 30` (Safety & Law 0.90 → 27; Street Lights 0.40 → 12) |
| Risk keywords | `min(30, 22 × max_weight + 4 × (n−1))` — worst keyword dominates, extras add a little |
| Vulnerable groups | `min(15, 20 × max_weight)` |
| Citizen distress | `10 × distress` |
| Duration | `min(10, 2 + 1.2 × days)` |
| Nearby similar open cases | `min(15, 4 × cluster_size)` |
| Repeat complaint | flat `6.0` if the text contains again/already/twice/still/ignored/reminder |

Bands: **Critical ≥ 60 · High ≥ 42 · Medium ≥ 25 · Low** below.

**Why a weighted rule engine instead of a trained priority model?** Two reasons.
(1) There is no ground-truth "correct priority" dataset to train on. (2) A public body must be
able to justify why complaint A jumped ahead of complaint B. Each `min()` cap exists to stop
one factor from monopolising the score — e.g. keyword stuffing can never exceed 30 points.

### Step 7 — Resolution recommendation (`recommend`, `engine.py:147`)
Three sources combined:
1. **SOP playbook** — the category's fixed 4–5 step playbook from `knowledge.py`, then
   **re-ordered** so steps sharing words with this specific complaint float to the top.
   Critical/High cases get *"Escalate to ward officer and field team within 2 hours"* inserted
   first. Vulnerable groups append an interim-safety step. Top 6 steps are returned.
2. **Proven past actions (retrieval)** — from the similar cases in Step 5, keep those that are
   `Resolved`, same category, and have a `resolution_note`; return the 3 most frequent notes
   with a `times_used` count. This is the "what actually worked" half.
3. **ETA** — the **median** `resolution_hours` of those resolved similar cases. No history?
   fall back to `SLA × 0.6`. Critical cases are further capped at `SLA × 0.5`.
   Median rather than mean, so one 3-week outlier doesn't wreck the estimate.

Plus **cross-department coordination** rules: dark street + women/harassment → also Police;
drainage/water + sick/mosquito/contaminated → also Health; tree + wire → Electricity;
garbage + burning → Environment.

### Step 8 — Title (`summarize`, `engine.py:183`)
First real sentence of the cleaned text, trimmed to ~80 characters at a word boundary,
capitalised, with the ward appended. Extractive, not generative — so it can never hallucinate.

**What `analyze()` returns:** category, confidence, alternatives, `needs_human_review`,
department, ward, title, sentiment, entities, priority_score, priority_level,
**priority_factors**, similar_cases, possible_duplicates, recommendation.

---

## 5. Saving it — `POST /api/grievances`

`services.create_grievance` (`services.py:35`):

1. Run `engine.analyze()` (the same call as the preview).
2. Resolve the ward to lat/lng from `WARDS`, plus a small random jitter (±0.008°) so multiple
   cases in one ward don't stack on a single map pin.
3. Generate the tracking ID: `SS-<year>-<00001>`.
4. `sla_due = created_at + SLA hours` for that category.
5. **Auto-route decision:** confident → status `Assigned`, `assigned_to = department`.
   Not confident → status `Submitted` and it waits for human triage.
6. Insert the row — including the entire analysis JSON blob in the `analysis` column, so the
   officer later sees exactly what the AI thought *at intake time*.
7. Write **timeline events** into the `events` table: "Grievance received via WhatsApp"
   (actor: Citizen), then "AI auto-routed to Electricity Board (Critical priority,
   98% confidence)" (actor: SamajSevak AI).
8. `refresh_index()` — the new case immediately becomes findable for the next complaint's
   duplicate check.

---

## 6. The output the citizen sees

- **Tracking ID**, the department it went to, the priority level.
- `/track/:id` → status timeline from the `events` table, SLA due date and whether it breached
  (`services._breached`: compares `resolved_at` — or *now* if still open — against `sla_due`).
- After resolution, a **1–5 star rating** → `POST /api/grievances/{id}/feedback`, stored on the
  row and appended to the timeline. This is the feedback loop that would feed retraining.

## 7. The output the officer sees

| Page | Endpoint | What's computed |
|---|---|---|
| **Priority Queue** | `GET /api/grievances` | SQL sorts open-before-closed, then `priority_score DESC`. Filters: status, category, priority, ward, free text |
| **Grievance Detail** | `GET /api/grievances/{id}` | Stored analysis + timeline + `live_similar` (similarity re-run against the *current* index, excluding itself) |
| **Command Center** | `GET /api/stats`, `/api/analytics` | Totals, critical open, SLA breached/at-risk (<12 h), SLA compliance %, avg resolution hours, satisfaction, 30-day daily trend, per-department scoreboard sorted **worst SLA first** |
| **Hotspots** | `GET /api/hotspots` | Per-ward open counts + top category (Leaflet/OpenStreetMap), plus per-case pins |
| **Alerts** | `GET /api/alerts` | Emerging-issue detection — see below |
| **AI Engine** | `GET /api/meta` + `/api/analyze` | Live sandbox: paste any text, see the raw pipeline output and the model metrics |
| **AI reply** | `POST /api/grievances/{id}/draft` | LLM or template citizen reply |

### Emerging-issue detection (`services.alerts`, `services.py:216`)
The one piece of analysis that looks at the **whole city**, not one complaint:

1. Bucket every grievance by `(ward, category)`.
2. `recent` = complaints in the last 7 days. `base` = days 7–28, divided by 3 → a weekly baseline.
3. `ratio = recent / max(baseline, 0.5)` (the 0.5 floor prevents division blow-ups on new wards).
4. Fire an alert when **≥ 4 cases this week AND ratio ≥ 2×**. Severity Critical at ≥ 4×.
5. The recommendation flips the framing: *"Launch a ward-level drive instead of case-by-case
   fixes"* — because 12 drainage complaints in one ward is one root cause, not 12 tickets.
6. Separately: any department with **≥ 3 open SLA-breached** cases gets an escalation alert.

### The optional LLM (`llm.py`)
Only used for drafting the citizen reply. The prompt is **grounded** — it is handed the
already-computed ID, category, priority, action plan and ETA, and is told "no false promises".
No key configured, or the API call throws? It silently returns `template_reply()` instead and
tags the response `provider: "template"`. **The LLM can never block the workflow, and it never
decides category, priority or routing** — those stay deterministic and auditable.

---

## 8. End-to-end, on the wire

```
Citizen types (Submit.jsx)
   │  debounce 500 ms
   ├─► POST /api/analyze ─► Engine.analyze() ─► live preview panel   [nothing saved]
   │
   └─► POST /api/grievances
          └─► services.create_grievance
                ├─ Engine.analyze()
                │     1 clean  2 classify+route  3 entities  4 sentiment
                │     5 similar/duplicates  6 priority+factors  7 recommend  8 title
                ├─ ward → lat/lng, ID = SS-2026-00123, sla_due
                ├─ INSERT grievances (+ analysis JSON)
                ├─ INSERT events × 2  (Citizen, SamajSevak AI)
                └─ refresh_index()
                       │
   ┌───────────────────┴───────────────────────────────┐
Citizen: ID + timeline + SLA          Officer: queue (priority DESC), detail with
+ 5-star feedback                     "why this priority", duplicates, action plan,
                                      ETA, AI-drafted reply, hotspot map, spike alerts
```

---

## 9. Design decisions worth defending

| Decision | Reason |
|---|---|
| Rule-based priority, not a model | No ground-truth labels exist; a public body must justify the ranking |
| TF-IDF + small embedding model, not a fine-tuned BERT | CPU-only, ~30 ms, about a minute to retrain; TF-IDF covers Hinglish, embeddings cover meaning and other scripts |
| Word **and** char n-grams | Char n-grams are what make Hinglish and typos work |
| Confidence gate at 0.40 | The model admits when it doesn't know instead of misrouting |
| Retrieval for "what worked" | Uses real outcomes, no generation, nothing to hallucinate |
| Median ETA, not mean | Robust to one pathological case |
| LLM strictly optional and grounded | Judges can run it with no API key; AI never silently invents a decision |
| Analysis JSON stored on the row | Full audit trail of what the AI concluded at intake |

## 10. What changed in v1.1 (read this with sections 2–9)

Sections 2–9 describe the original pipeline; the line numbers in them have shifted.
These five things are different now:

1. **Languages** (`app/lang.py`, lexicons in `knowledge.py`). Every complaint gets a detected
   language. English, Hinglish, Hindi and Marathi run the full pipeline: Hindi / Marathi risk
   words, vulnerable groups, ward names, durations ("3 दिन से", "दोन आठवड्यांपासून") and landmarks are
   mapped onto the same English keys the priority score already used, so "why this priority"
   reads the same in every language. Any other script is recognised, gets a category suggestion,
   and is always sent to human review. The citizen pages and the Speak button switch between
   English / हिंदी / मराठी, and template replies are written in the complaint's language.
2. **Embeddings** (`app/ml/embed.py`, `train.py`). The classifier is now the average of the
   old TF-IDF model and a Logistic Regression on multilingual sentence embeddings
   (MiniLM, ONNX on CPU, no PyTorch). TF-IDF still carries Hinglish, which the embedding model
   does not understand; embeddings carry meaning and other scripts. The similarity index uses
   both, so a Marathi report matches an English report of the same incident. If the model
   files are missing the engine runs on TF-IDF alone.
3. **GPS duplicates** (`app/geo.py`, `Engine.analyze`). The form captures a GPS fix or a map
   pin. With coordinates on both reports, distance decides: same category + open + within 300 m
   (similarity ≥ 0.45, or ≥ 0.35 within 100 m) is a possible duplicate; within 500 m counts toward
   the cluster size. An open same-category case within 100 m is a candidate even with no shared
   wording. Without GPS on either side it falls back to the old same-ward rule. Seed data
   simulates GPS by placing all complaints about one landmark in a ward within ~50 m.
4. **Photo evidence** (`services.decode_photo`, `llm.check_photo`). Photos are shrunk in the
   browser, validated (JPEG/PNG/WebP, ≤ 3 MB), stored on disk and shown only to logged-in
   officers. Officers can attach a proof photo when resolving; the citizen sees it on the
   tracking page. With an LLM key a vision model reports whether the photo shows the complaint
   (advisory; it never changes routing or priority). Without a key there is no automatic check.
5. **Login** (`app/auth.py`). All officer endpoints need a bearer token (PBKDF2 password hash,
   HMAC-signed token, 8 h expiry, lockout after 5 failed attempts). Citizens use
   `/api/track/{id}`, which returns no name, phone, coordinates or AI internals. The audit
   trail records the signed-in officer.

The feedback loop from section 6 is now real: an officer's *Confirm / Correct category*
stores a verified label, and *Retrain* on the AI Engine page trains on templates + verified
complaints (weighted 10×) and swaps the model in.

*Measured accuracy now* (`backend/models/metrics.json`): 87.9% (58/66) on the English + Hinglish
final set (TF-IDF alone: 80.3%), 55 auto-routed, 4 of them wrongly. Hindi 100% and Marathi 97.0%
on 33 hand-written complaints each — optimistic, because the templates are translations by the
same author; before any Hindi / Marathi training text existed the figures were 90.9% and 84.8%.
Full analysis takes about 30 ms per complaint on CPU.

## 10a. What changed in v1.2: master issues, citizen verification, escalation

- **Data model.** Every row in `grievances` is one citizen report. The report whose `master_id` is its own
  id is the master issue and carries the operational state (status, assignee, stage, resolution); that
  state is copied onto every report linked to it (`services._sync`). `association_source` says who made
  the link: `CITIZEN`, `AI` or `OFFICER`. New table `citizens`; events gained `actor_type`, `prev_state`,
  `new_state`.
- **Manual join first** (`Submit.jsx`, `services.issue_cards`). `/api/analyze` returns up to three open
  issues near the complaint. If the citizen joins one, `create_grievance` links it and skips the AI check.
- **AI fallback** (`services.find_master`). Runs only when nothing was joined. Rules: GPS on both and
  within 300 m with wording ≥ 0.45 (≥ 0.35 within 100 m) or a matching photo; without GPS, same ward and
  (wording ≥ 0.6 with the same landmark, or a matching photo with wording ≥ 0.35). If the citizen was
  shown an issue and reported separately, that is recorded, and the AI may still link it on this evidence.
- **Categories.** The AI's category, the citizen's choice and the final category are stored separately
  with `classification_source` (AI / CITIZEN / OFFICER). A confident disagreement goes to human triage.
- **Image reuse** (`services.photo_hashes`). SHA-256 plus a difference hash (Pillow), ≤ 6 differing bits.
- **Satisfaction** (`services.feedback`). Resolved → citizen answers → Closed or Not Satisfied. With several
  citizens on an issue, one "not satisfied" keeps it open; re-resolving asks everyone again.
- **Escalation** (`services.run_escalations`, config in `knowledge.ESCALATION_STAGES`). Checked lazily, at
  most once a minute, whenever a page is loaded. Resolved issues are not escalated; Not Satisfied resumes
  the clock where it stopped. Each move writes an event with the previous and new stage.
- **Privacy.** `services.officer_view` strips name, phone and abuse-signal inputs from every officer
  response; new reports do not store name or phone on the report at all.

## 10b. Honest limitations

- The escalation ladder and its durations are this prototype's design, not a legal procedure. Escalating
  changes records and screens only: there are no accounts for the higher authorities and nothing is sent
  to them.
- Citizen login is name + mobile with no OTP, so anyone who knows both can sign in as that citizen.
- With no `SAMAJSEVAK_SECRET` set, the salt for network hashes changes on every restart, so the "same
  network" signal only works within one run.

- The base training data is still **synthetic templates**. The officer-verification loop is
  built, but no real complaints have been collected, so there is no accuracy figure on real text.
- Full support is four languages (English, Hinglish, Hindi, Marathi). Other languages only get a
  category suggestion and go to human review; Roman-script Marathi is not handled.
- Embeddings do not read Hinglish, so cross-language duplicate matching for Hinglish relies on
  the 100 m location rule.
- The photo check needs a Gemini / OpenAI key and has only been tested against a mocked
  response. Photo EXIF location is not read.
- One shared officer account from environment variables; no roles. Tracking IDs are sequential,
  so the public status page of another complaint can be guessed (it shows no personal fields,
  but it does show the complaint text). Suggested issues show the first sentence of the original
  complaint as their title.
- SQLite and the in-memory index are single-process; real scale needs PostgreSQL + a vector store.

---

## 11. Run it

```bash
# backend
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m app.ml.train            # optional — a trained model ships with the repo
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173

# or everything in one container
docker build -t samajsevak . && docker run -p 8000:8000 samajsevak
```

API docs: <http://localhost:8000/docs> · Tests: `cd backend && pytest -q`
