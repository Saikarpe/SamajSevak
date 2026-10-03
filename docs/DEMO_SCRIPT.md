# SamajSevak — Demo Script (Hack2Ignite · AI-04)

A presenter's run sheet: **what to click, what to paste, which image to use, and what to say**.
Total ≈ 10 minutes. Every prompt below was run through the real AI engine; the expected
results are noted next to each one. Scores can move by a few points as data changes.

---

## 0. Before you go on stage (prep checklist)

| ✔ | Item | Detail |
|---|---|---|
| ☐ | Backend running | `cd backend && .venv\Scripts\activate && uvicorn app.main:app --port 8000` |
| ☐ | Frontend running | `cd frontend && npm run dev` → http://localhost:5173 |
| ☐ | Officer login | `officer` / `samajsevak-demo` (shown on the login page when `OFFICER_PASSWORD` is not set) |
| ☐ | Two browser windows | **Window A** = citizen (`/citizen`), **Window B** = officer (logged in at `/`) |
| ☐ | Photos ready on desktop | See section 7 (Image plan) |
| ☐ | Prompts ready to paste | Keep this file open on a second screen |
| ☐ | Location permission | Allow it in the browser once, so *Use my location* doesn't pop a dialog mid-demo |
| ☐ | Backup | `docs/screenshots/*.png` + the PPT, in case Wi-Fi or the laptop fails |

> Tip: do one full dry run. Reports you file become part of the data, so later "join this issue" suggestions will include them, which is fine and actually helps the story.

---

## 1. The hook (30 s) — slide / no clicks

**Say:**
> "Every city receives thousands of complaints a day: in English, Hindi, Marathi, Hinglish, with photos, without addresses. Officers read them one by one, the same pothole gets reported fifty times, and urgent ones like a live wire wait behind a streetlight complaint. SamajSevak turns each raw complaint into a **prioritised, routed, explained case**, tells the officer **how** to fix it, and keeps the department **accountable** until the citizen says it's fixed."

**Show:** `docs/screenshots/dashboard.png` (or the PPT title slide).

---

## 2. Act 1 — The citizen (≈ 3 min) · Window A → `/citizen`

### Step 2.1 — English, critical safety issue
**Paste:**
```
Live electric wire has fallen near the primary school in Kothrud since yesterday. Children walk here daily, extremely dangerous!
```
**Image:** `fallen_wire.jpg` (optional)
**Expected (live preview, before submitting):** Electricity · ~94% confidence · Electricity Board · Kothrud · **Critical ~73/100**

**Point at:**
1. The **AI Triage** panel filling in *as you type*: nothing is saved yet.
2. **"Why this priority?"**: each factor with its points (category severity, "live wire", children = vulnerable group, distress, duration).
3. **"Already reported nearby?"**: an open issue is suggested. Click **Join this issue**.

**Say:**
> "The AI never just says 'Critical'. It shows the officer exactly why: live wire, children, one day old. And before filing, the citizen sees that someone already reported this, so one real problem stays **one master issue**, not fifty tickets."

**Reference image:** `docs/screenshots/submit.png`

### Step 2.2 — Multilingual (switch the language tabs: हिंदी / मराठी)
Paste one at a time and let the preview update. You don't need to submit all of them.

| Language | Prompt | Expected result |
|---|---|---|
| **Hinglish** | `Wakad mein hamari society mein 4 din se nal mein pani nahi aa raha, tanker bhi nahi aaya` | Water Supply · Wakad · High ~45 |
| **Hindi** | `हडपसर में सब्जी मंडी के पीछे नाली का गंदा पानी 5 दिन से सड़क पर बह रहा है, बहुत बदबू है।` | Drainage & Sewage · Hadapsar · **Critical ~63** |
| **Marathi** | `कोथरूड मध्ये गणेश मंदिराजवळ रस्त्यावर मोठा खड्डा आहे, दोन आठवड्यांपासून कोणीही दुरुस्त केलेला नाही, काल एका दुचाकीचा अपघात झाला.` | Roads & Potholes · Kothrud · High ~46 |

**Say:**
> "Same pipeline, four languages. Ward, duration ('5 दिन से', 'दोन आठवड्यांपासून') and risk words like 'अपघात' are mapped to one vocabulary, so the officer's explanation reads the same whatever language the citizen used."

**Optional:** click **Speak** and say the Hindi sentence aloud (browser speech recognition, Chrome works best).

### Step 2.3 — Photo + GPS, then submit
**Paste:**
```
Katraj mein main chowk pe bahut bada pothole hai 2 hafte se, kal accident hua
```
**Image:** `pothole.jpg`
**Do:** *Add a photo* → *Use my location* (or drop a pin on the map in Katraj) → **Submit**.

**Point at:** the **Tracking ID** (`SS-2026-xxxxx`), department, SLA. Write the ID down; you'll need it in Act 4.

### Step 2.4 — The honesty valve (low confidence)
**Paste:**
```
There is a problem near my house, please look into it.
```
**Expected:** confidence ~28% → **Needs human review**, not auto-routed.

**Say:**
> "When the model is under 40% confident, it says so and sends the complaint to a human. It doesn't guess the department."

---

## 3. Act 2 — The officer (≈ 4 min) · Window B

### Step 3.1 — Command Center `/`
**Image:** `docs/screenshots/dashboard.png`
**Point at:** KPIs (open, critical, SLA breached / at risk, compliance %), the 30-day trend, AI alerts, department scoreboard sorted **worst SLA first**.

### Step 3.2 — Priority Queue `/grievances`
**Image:** `docs/screenshots/queue.png`
**Point at:** the Kothrud live-wire issue near the top. One row per **master issue**, with a report count. Filter by ward or category.

**Say:**
> "The officer doesn't read 500 complaints in order of arrival. They start with what is most dangerous, and every rank can be explained."

### Step 3.3 — Grievance Detail (open the live-wire issue)
**Image:** `docs/screenshots/detail.png`
Walk top to bottom:
1. **AI triage + "why this priority"**: the same factor breakdown the citizen saw.
2. **Linked reports**: every report under this master issue, *who* linked it (`CITIZEN` / `AI` / `OFFICER`) and the evidence (distance, wording, photo match). The officer can confirm, detach or re-link.
3. **Recommended resolution plan**: SOP steps re-ordered for this complaint, "escalate within 2 hours" because it's Critical, plus an interim safety step because of children.
4. **Proven past actions**: what actually fixed similar past cases, with "used N times", and the **ETA** (median of real past resolution times).
5. **Confirm / correct category**: click *Confirm*. "This becomes a verified training label."
6. **Draft citizen reply**: click it. Without an API key it uses a template in the citizen's language; with a Gemini/OpenAI key the LLM drafts it, grounded on the facts above.
7. **Resolve with proof photo**: change status to Resolved and attach `pothole_fixed.jpg` / `wire_fixed.jpg`.

**Say:**
> "The AI decides nothing silently. Category, priority and routing are deterministic and auditable; the LLM only writes the reply, and the demo works without it."

### Step 3.4 — Cross-department coordination (quick, optional)
Paste into **AI Engine** `/ai-lab` (sandbox, nothing saved):

| Prompt | Expected |
|---|---|
| `Street lights near the bus stop in Yerawada have been off for a week. Women feel unsafe walking home at night and there was harassment yesterday.` | Street Lights · High ~49 · **coordinate with Police & Public Safety Cell** |
| `Complaining again! Garbage has not been collected in our colony in Baner for 10 days, it is still lying there and people are burning it.` | Garbage · High ~45 · **+Repeat complaint** points · coordinate with **Environment Dept** |
| `Street light in lane no. 4 in Aundh is flickering at night.` | Street Lights · **Low ~12** (contrast with the live wire) |

**Image:** `docs/screenshots/ailab.png`, which also shows model metrics.

---

## 4. Act 3 — City-level intelligence (≈ 1.5 min) · `/insights`

**Image:** `docs/screenshots/insights.png`
**Point at:**
1. **Hotspot map** (OpenStreetMap) and **ward risk ranking**.
2. **Emerging-issue alert**: the Hadapsar drainage/health spike (≥ 2× the 3-week baseline and ≥ 4 cases this week).
3. **Department SLA performance.**

**Say:**
> "Twelve drainage complaints in one ward in one week is not twelve tickets, it's one root cause. The system tells the commissioner to run a ward-level drive instead of fixing them one by one."

---

## 5. Act 4 — Closing the loop and accountability (≈ 1.5 min) · Window A

### Step 5.1 — Track `/track/<your ID>`
**Image:** `docs/screenshots/track.png`
**Point at:** the status timeline, current **escalation stage**, SLA, and the officer's **proof photo**.

### Step 5.2 — Citizen verification
Sign in at **My Complaints** `/my` (name + mobile) → choose **Not satisfied**.
**Say:**
> "Resolved only means 'awaiting citizen confirmation'. One 'not satisfied' reopens the issue for everyone on it. Silence is never treated as satisfied."

### Step 5.3 — Escalation ladder (explain; don't wait for the timer)

| Stage | Held by |
|---|---|
| Complaint | Concerned department |
| Warning | Concerned department |
| Strike 1 | Higher authority of the department |
| Strike 2 | Deputy Collector |
| Strike 3 | Final escalation body |

> Be upfront that the ladder and its durations are the prototype's own design, and that nothing is sent to real authorities.

### Step 5.4 — Public Accountability `/public`
**Image:** `docs/screenshots/public.png`
**Say:** "Anyone can see aggregate counts: received, resolved, pending, by stage, department and ward. No personal data."

---

## 6. Close (30 s)

> "Raw complaint in any of four languages → category, department, explained priority, duplicate merging, an action plan from real past fixes, an ETA → escalation until the citizen confirms. It runs entirely on a CPU, about 30 ms per complaint, with no API key needed. Officer corrections become training data, so it improves with use."

Then: honest accuracy (next section) and the roadmap (WhatsApp intake, more languages, OTP, PostGIS, CPGRAMS integration).

---

## 7. Image plan (what to keep on your desktop)

`backend/data/uploads/` is empty, so bring your own photos (phone pictures or free stock images; JPEG/PNG/WebP, ≤ 3 MB).

| File | Used in | Purpose |
|---|---|---|
| `pothole.jpg` | Step 2.3 | Evidence photo with the Katraj complaint |
| `pothole.jpg` **again** (2nd citizen, same spot) | Optional duplicate demo | Same image → SHA-256 / difference-hash match → AI links it to the same master issue |
| `fallen_wire.jpg` | Step 2.1 | Evidence for the critical case |
| `pothole_fixed.jpg` or `wire_fixed.jpg` | Step 3.3 | Officer's **proof of resolution**, which the citizen sees on Track |
| `garbage.jpg` | Spare | Backup prompt / photo |

**Screenshots for slides or backup** (already in `docs/screenshots/`):

| File | Screen |
|---|---|
| `submit.png` | Citizen form + live AI triage + "join this issue" |
| `dashboard.png` | Command Center |
| `queue.png` | Priority Queue |
| `detail.png` | Grievance detail: plan, duplicates, reply |
| `insights.png` | Hotspot map + alerts |
| `ailab.png` | AI Engine sandbox + metrics |
| `track.png` | Citizen tracking timeline |
| `public.png` | Public accountability page |

---

## 8. Prompt bank (all verified on the engine)

| # | Language | Prompt | Category | Priority |
|---|---|---|---|---|
| 1 | English | Live electric wire has fallen near the primary school in Kothrud since yesterday. Children walk here daily, extremely dangerous! | Electricity (94%) | Critical ~73 |
| 2 | Hinglish | Wakad mein hamari society mein 4 din se nal mein pani nahi aa raha, tanker bhi nahi aaya | Water Supply (60%) | High ~45 |
| 3 | Hinglish | Katraj mein main chowk pe bahut bada pothole hai 2 hafte se, kal accident hua | Roads & Potholes (64%) | High ~46 |
| 4 | Hindi | हडपसर में सब्जी मंडी के पीछे नाली का गंदा पानी 5 दिन से सड़क पर बह रहा है, बहुत बदबू है। | Drainage & Sewage (73%) | Critical ~63 |
| 5 | Hindi | स्वारगेट में बस स्टॉप के पास बिजली का तार टूटकर गिरा है, बहुत खतरनाक है, बच्चे यहाँ से गुजरते हैं। | Electricity (71%) | High ~58 |
| 6 | Hindi | हडपसर में 3 दिन से नल में पानी नहीं आ रहा है, बुजुर्गों को बहुत परेशानी है। | Water Supply (84%) | High ~56 |
| 7 | Marathi | कोथरूड मध्ये गणेश मंदिराजवळ रस्त्यावर मोठा खड्डा आहे, दोन आठवड्यांपासून कोणीही दुरुस्त केलेला नाही, काल एका दुचाकीचा अपघात झाला. | Roads & Potholes (74%) | High ~46 |
| 8 | English | Street lights near the bus stop in Yerawada have been off for a week. Women feel unsafe walking home at night and there was harassment yesterday. | Street Lights + **Police** | High ~49 |
| 9 | English | Complaining again! Garbage has not been collected in our colony in Baner for 10 days, it is still lying there and people are burning it. | Garbage + **Environment** | High ~45 |
| 10 | English | Street light in lane no. 4 in Aundh is flickering at night. | Street Lights (99%) | Low ~12 |
| 11 | English | There is a problem near my house, please look into it. | — | **Human review** (28%) |

> Avoid: the shorter Hinglish "Pani nahi aa raha hai 4 din se…" and the Hindi "…मच्छर बहुत बढ़ गए हैं…" variants. They fall below the confidence gate and go to human review, which is correct behaviour but not what you want in the multilingual step.

---

## 9. Likely judge questions (short answers)

| Question | Answer |
|---|---|
| What model is it? | Two small models averaged: TF-IDF (word + char n-grams, which handle Hinglish and typos) and multilingual MiniLM embeddings (ONNX, CPU), each with Logistic Regression over 11 categories. |
| Why not an LLM for everything? | Routing and priority must be explainable and reproducible for a public body. The LLM is optional and only drafts replies. |
| How accurate? | **87.9% (58/66)** on a hand-written English + Hinglish set written after training was frozen. Synthetic test numbers (99%+) are not the ones to quote. Hindi and Marathi zero-shot: 90.9% / 84.8%. |
| Where's the training data from? | Synthetic templates for now. Officer *Confirm / Correct* stores verified labels, and *Retrain* weights them 10× and hot-swaps the model. |
| How is priority computed? | An additive, capped rule score (severity, risk words, vulnerable groups, distress, duration, cluster size, repeat). No ground-truth priority labels exist, and every point must be justifiable. |
| How do you detect duplicates? | Citizen joins first. Otherwise the AI links only on combined evidence: GPS within 300 m plus a wording or photo match, or same ward plus a strong wording match and the same landmark. Ward or category alone never merges. |
| Privacy? | Officers see `CIT-00012`, never name or phone. Network address is a salted hash kept 30 days. Public pages show aggregates only. |
| Limitations? | No OTP yet, sequential tracking IDs, one shared officer account, synthetic base data, escalation not sent to real authorities, SQLite single-process. |
