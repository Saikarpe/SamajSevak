"""SamajSevak AI engine: classification, sentiment, entity extraction, explainable
priority scoring, duplicate detection and resolution recommendation."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.knowledge import (CATEGORIES, INTENSIFIERS, NEGATIVE_WORDS, POSITIVE_WORDS, URGENCY_TERMS,
                           VULNERABLE_TERMS, WARDS)

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "classifier.joblib"
WORD_RE = re.compile(r"[a-z']+")
BOILERPLATE = re.compile(
    r"(respected sir,?|dear team,?|hello,?|sir/madam,?|this is to bring to your notice that|i want to complain that|"
    r"kindly look into this:?|please help\.?|please take action\.?|kindly resolve urgently\.?|please do the needful\.?|"
    r"nobody is responding to our calls\.?|we are really frustrated\.?|complaint already given twice but still ignored\.?|"
    r"thank you\.?)", re.I)


def core_text(text: str) -> str:
    """Strip greetings / sign-offs so similarity focuses on the actual issue."""
    return " ".join(BOILERPLATE.sub(" ", text).split()) or text


class Engine:
    def __init__(self):
        if not MODEL_PATH.exists():
            from app.ml import train
            train.main()
        self.clf = joblib.load(MODEL_PATH)
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.corpus_rows: list[dict] = []

    # ---------------- similarity index ----------------
    def build_index(self, rows: list[dict]):
        self.corpus_rows = rows
        if not rows:
            self.vectorizer, self.matrix = None, None
            return
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.matrix = self.vectorizer.fit_transform([core_text(r["text"]) for r in rows])

    def similar(self, text: str, k: int = 5, exclude_id: str | None = None, category: str | None = None):
        if self.vectorizer is None:
            return []
        sims = cosine_similarity(self.vectorizer.transform([core_text(text)]), self.matrix)[0]
        if category:  # semantic + category-aware re-ranking
            same = np.array([r["category"] == category for r in self.corpus_rows])
            sims = np.where(same, sims + 0.1, sims * 0.6)
        order = np.argsort(-sims)
        out = []
        for i in order:
            r = self.corpus_rows[i]
            if r["id"] == exclude_id:
                continue
            if sims[i] < 0.12 or len(out) >= k:
                break
            out.append({**r, "similarity": round(min(1.0, float(sims[i])), 3)})
        return out

    # ---------------- components ----------------
    def classify(self, text: str):
        probs = self.clf.predict_proba([text])[0]
        classes = self.clf.classes_
        order = np.argsort(-probs)[:3]
        top = [{"category": str(classes[i]), "confidence": round(float(probs[i]), 3)} for i in order]
        return top

    @staticmethod
    def sentiment(text: str):
        words = WORD_RE.findall(text.lower())
        neg = pos = 0.0
        for i, w in enumerate(words):
            boost = 1.5 if i > 0 and words[i - 1] in INTENSIFIERS else 1.0
            if w in NEGATIVE_WORDS:
                neg += boost
            elif w in POSITIVE_WORDS:
                pos += 1
        exclaim = text.count("!")
        caps = sum(1 for t in text.split() if len(t) > 3 and t.isupper())
        raw = pos - neg - 0.5 * exclaim - 0.5 * caps
        score = max(-1.0, min(1.0, raw / 4))
        distress = round(max(0.0, min(1.0, (neg + 0.5 * exclaim + 0.5 * caps) / 4)), 2)
        label = "Negative" if score < -0.15 else "Positive" if score > 0.25 else "Neutral"
        emotion = "Anger/Frustration" if distress >= 0.5 else "Concern" if distress > 0.1 else "Calm"
        return {"score": round(score, 2), "label": label, "distress": distress, "emotion": emotion}

    @staticmethod
    def entities(text: str):
        low = text.lower()
        ward = next((w for w in WARDS if w.lower() in low), None)
        days = None
        m = re.search(r"(\d+|one|two|three|four|five|six|seven|ten)\s*(day|days|week|weeks|month|months)", low)
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10}
        if m:
            n = int(m.group(1)) if m.group(1).isdigit() else words[m.group(1)]
            unit = m.group(2)
            days = n * (7 if unit.startswith("week") else 30 if unit.startswith("month") else 1)
        elif "yesterday" in low:
            days = 1
        elif "last month" in low:
            days = 30
        landmark = None
        lm = re.search(r"\b(near|opposite|behind|next to|beside|outside|in front of)\s+(the\s+)?([a-z0-9 .'-]{3,40}?)(?=[,.]| in | and |$)", low)
        if lm:
            landmark = (lm.group(1) + " " + (lm.group(3) or "")).strip()
        found = {t for t in URGENCY_TERMS if re.search(rf"\b{re.escape(t)}", low)}
        found = {t for t in found if not any(t != o and t in o for o in found)}  # drop 'danger' if 'dangerous'
        urgency = sorted(found, key=lambda t: -URGENCY_TERMS[t])
        vulnerable = sorted({t for t in VULNERABLE_TERMS if re.search(rf"\b{re.escape(t)}\b", low)})
        return {"ward": ward, "duration_days": days, "landmark": landmark,
                "urgency_terms": urgency, "vulnerable_groups": vulnerable}

    def priority(self, category: str, ents: dict, senti: dict, cluster_size: int, repeat: bool):
        factors = []
        sev = CATEGORIES[category]["severity"]
        factors.append({"factor": f"Category severity ({category})", "points": round(sev * 30, 1)})
        if ents["urgency_terms"]:
            w = [URGENCY_TERMS[t] for t in ents["urgency_terms"]]
            pts = min(30, 22 * max(w) + 4 * (len(w) - 1))
            factors.append({"factor": "Risk keywords: " + ", ".join(ents["urgency_terms"][:4]), "points": round(pts, 1)})
        if ents["vulnerable_groups"]:
            w = max(VULNERABLE_TERMS[t] for t in ents["vulnerable_groups"])
            factors.append({"factor": "Vulnerable groups affected: " + ", ".join(ents["vulnerable_groups"][:3]),
                            "points": round(min(15, 20 * w), 1)})
        if senti["distress"] > 0:
            factors.append({"factor": f"Citizen distress ({senti['emotion']})", "points": round(10 * senti["distress"], 1)})
        if ents["duration_days"]:
            d = ents["duration_days"]
            factors.append({"factor": f"Issue persisting ~{d} day(s)", "points": round(min(10, 2 + 1.2 * d), 1)})
        if cluster_size > 0:
            factors.append({"factor": f"{cluster_size} similar open complaint(s) nearby", "points": round(min(15, 4 * cluster_size), 1)})
        if repeat:
            factors.append({"factor": "Repeat complaint / earlier ignored", "points": 6.0})
        score = round(min(100.0, sum(f["points"] for f in factors)), 1)
        level = "Critical" if score >= 60 else "High" if score >= 42 else "Medium" if score >= 25 else "Low"
        return score, level, factors

    # ---------------- recommendations ----------------
    def recommend(self, text: str, category: str, level: str, ents: dict, similar: list[dict]):
        low = text.lower()
        steps = list(CATEGORIES[category]["playbook"])
        # context-aware reordering: bubble up steps sharing words with the complaint
        kw = set(WORD_RE.findall(low))
        steps.sort(key=lambda s: -len(kw & set(WORD_RE.findall(s.lower()))))
        if level in ("Critical", "High"):
            steps.insert(0, "Escalate to ward officer and field team within 2 hours (high-risk case)")
        if ents["vulnerable_groups"]:
            steps.append("Inform citizen of interim safety measures for " + ", ".join(ents["vulnerable_groups"]))
        resolved = [s for s in similar if s.get("status") == "Resolved" and s.get("resolution_note")
                    and s.get("category") == category]
        proven = Counter(s["resolution_note"] for s in resolved).most_common(3)
        hours = [s["resolution_hours"] for s in resolved if s.get("resolution_hours")]
        sla = CATEGORIES[category]["sla_hours"]
        eta = round(float(np.median(hours)), 1) if hours else sla * 0.6
        if level == "Critical":
            eta = min(eta, sla * 0.5)
        cross = []
        if category == "Street Lights" and any(t in low for t in ("unsafe", "women", "harassment", "afraid")):
            cross.append("Police & Public Safety Cell")
        if category in ("Drainage & Sewage", "Water Supply") and any(t in low for t in ("sick", "fever", "vomiting", "diarrhea", "mosquito", "contaminated")):
            cross.append("Health Department")
        if category == "Tree & Parks" and "wire" in low:
            cross.append("Electricity Board")
        if category == "Garbage & Sanitation" and "burning" in low:
            cross.append("Environment Department")
        return {
            "action_plan": steps[:6],
            "proven_resolutions": [{"action": a, "times_used": c} for a, c in proven],
            "estimated_resolution_hours": eta,
            "sla_hours": sla,
            "coordinate_with": cross,
        }

    @staticmethod
    def summarize(text: str, category: str, ward: str | None):
        body = core_text(text)
        sentences = [x for x in re.split(r"(?<=[.!?])\s+", body) if len(x) > 8] or [body]
        core = sentences[0].strip()
        if len(core) > 80:
            cut = core[:80]
            core = cut[:cut.rfind(" ")].rstrip(" ,.") + "…"
        core = core.rstrip(" .")
        core = core[0].upper() + core[1:] if core else category
        return core + (f" — {ward}" if ward and ward.lower() not in core.lower() else "")

    # ---------------- full pipeline ----------------
    def analyze(self, text: str, ward: str | None = None, exclude_id: str | None = None):
        top = self.classify(text)
        category = top[0]["category"]
        ents = self.entities(text)
        ward = ward or ents["ward"]
        senti = self.sentiment(text)
        similar = self.similar(text, k=8, exclude_id=exclude_id, category=category)
        same_area_open = [s for s in similar if s.get("ward") == ward and s.get("category") == category
                          and s.get("status") != "Resolved" and s["similarity"] >= 0.25]
        duplicates = [s for s in same_area_open if s["similarity"] >= 0.55]
        repeat = any(t in text.lower() for t in ("again", "already", "twice", "still", "ignored", "reminder"))
        score, level, factors = self.priority(category, ents, senti, len(same_area_open), repeat)
        rec = self.recommend(text, category, level, ents, similar)
        needs_review = top[0]["confidence"] < 0.40
        slim = lambda s: {k: s.get(k) for k in ("id", "title", "category", "ward", "status", "similarity", "resolution_note", "created_at")}
        return {
            "category": category,
            "confidence": top[0]["confidence"],
            "alternatives": top[1:],
            "needs_human_review": needs_review,
            "department": CATEGORIES[category]["department"],
            "ward": ward,
            "title": self.summarize(text, category, ward),
            "sentiment": senti,
            "entities": ents,
            "priority_score": score,
            "priority_level": level,
            "priority_factors": factors,
            "similar_cases": [slim(s) for s in similar[:5]],
            "possible_duplicates": [slim(s) for s in duplicates[:3]],
            "recommendation": rec,
        }


engine = Engine()
