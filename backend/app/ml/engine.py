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

from app import geo, lang
from app.knowledge import (CATEGORIES, INTENSIFIERS, NEGATIVE_STEMS, NEGATIVE_WORDS, POSITIVE_WORDS, REPEAT_TERMS,
                           URGENCY_ALIASES, URGENCY_TERMS, VULNERABLE_ALIASES, VULNERABLE_TERMS, WARD_ALIASES, WARDS)
from app.ml import embed, train

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "classifier.joblib"
DEV = lang.DEV
WORD_RE = re.compile(rf"[a-z']+|[{DEV}]+")
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+")
BOILERPLATE = re.compile(
    r"(respected sir,?|dear team,?|hello,?|sir/madam,?|this is to bring to your notice that|i want to complain that|"
    r"kindly look into this:?|please help\.?|please take action\.?|kindly resolve urgently\.?|please do the needful\.?|"
    r"nobody is responding to our calls\.?|we are really frustrated\.?|complaint already given twice but still ignored\.?|"
    r"thank you\.?|महोदय,?|नमस्कार,?|आपको सूचित करना है कि|कृपया ध्यान दें:?|कृपया कार्रवाई करें।?|जल्द से जल्द समाधान करें।?|"
    r"धन्यवाद[।.]?|आपल्या निदर्शनास आणू इच्छितो की|कृपया लक्ष द्या:?|कृपया कारवाई करा\.?|लवकरात लवकर उपाय करा\.?)", re.I)

# similarity: embedding cosine is rescaled so its thresholds line up with TF-IDF cosine
EMB_FLOOR, EMB_SPAN = 0.45, 0.5
SIM_FLOOR, SIM_CLUSTER, SIM_DUPLICATE = 0.12, 0.25, 0.55
CLUSTER_RADIUS_M, DUPLICATE_RADIUS_M = 500, 300
CLOSED_STATUSES = ("Resolved", "Closed", "Rejected")  # no longer an open workload

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10,
             "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "panch": 5, "chhe": 6, "saat": 7, "aath": 8, "das": 10,
             "एक": 1, "एका": 1, "दो": 2, "दोन": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "पाच": 5, "छह": 6, "सहा": 6,
             "सात": 7, "आठ": 8, "दस": 10, "दहा": 10, "पंद्रह": 15, "पंधरा": 15}
UNITS = [("day|din|divas|दिन|दिवस", 1), ("week|haft|athavd|हफ्त|हफ़्त|सप्ताह|आठवड", 7), ("month|mahin|महीन|महिन", 30)]
DURATION_RE = re.compile(
    rf"(?<![a-z{DEV}])(\d+|" + "|".join(sorted(map(lang.norm, NUM_WORDS), key=len, reverse=True)) + r")\s*("
    + "|".join(lang.norm(u) for u, _ in UNITS) + ")")
FIXED_DURATIONS = [(("yesterday", "कल से", "कल रात से", "कालपासून", "काल रात्रीपासून", "kal se"), 1),
                   (("आठवडाभर", "हफ्ते भर", "hafte bhar"), 7), (("last month", "महीने भर", "महिनाभर"), 30)]
LANDMARK_RES = [
    re.compile(r"\b(near|opposite|behind|next to|beside|outside|in front of)\s+(?:the\s+)?([a-z0-9 .'-]{3,40}?)(?=[,.]| in | and |$)"),
    re.compile(rf"([{DEV}]+(?:\s+[{DEV}]+)?\s+के (?:पास|सामने|पीछे|बाहर|बगल में))"),
    re.compile(rf"((?:[{DEV}]+\s+)?[{DEV}]*(?:जवळ|समोर|शेजारी|बाहेर))(?![{DEV}])"),
    re.compile(r"((?:[a-z]+\s+){1,2}ke (?:paas|pass|samne|saamne|peeche|bahar))"),
]


def _term_res(english: dict, aliases: dict, full_word: bool):
    """(regex, surface, english key). English terms keep their original matching rule;
    short Devanagari / single-word Hinglish aliases must match a whole word."""
    out = [(re.compile(rf"\b{re.escape(t)}" + (r"\b" if full_word else "")), t, t) for t in english]
    for surface, key in aliases.items():
        s = lang.norm(surface)
        if s.isascii():
            rx = rf"\b{re.escape(s)}" + ("" if " " in s else r"\b")
        else:
            rx = rf"(?<![{DEV}]){re.escape(s)}" + (rf"(?![{DEV}])" if len(s) <= 3 else "")
        out.append((re.compile(rx), s, key))
    return out


URGENCY_RES = _term_res(URGENCY_TERMS, URGENCY_ALIASES, full_word=False)
VULNERABLE_RES = _term_res(VULNERABLE_TERMS, VULNERABLE_ALIASES, full_word=True)


def _match(res, low: str) -> set[str]:
    hits = [(s, key) for rx, s, key in res if rx.search(low)]
    # drop 'danger' if 'dangerous' also matched
    return {key for s, key in hits if not any(s != o and s in o for o, _ in hits)}


def core_text(text: str) -> str:
    """Strip greetings / sign-offs so similarity focuses on the actual issue."""
    return " ".join(BOILERPLATE.sub(" ", text).split()) or text


class Engine:
    def __init__(self):
        if not MODEL_PATH.exists():
            train.main()
        self.load()
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.emb_matrix = None
        self.corpus_rows: list[dict] = []

    def load(self):
        model = joblib.load(MODEL_PATH)
        if not isinstance(model, dict):  # model file from before embeddings were added
            model = {"tfidf": model, "emb": None}
        if not embed.available():
            model["emb"] = None
        self.model = model

    # ---------------- similarity index ----------------
    def build_index(self, rows: list[dict]):
        self.corpus_rows = rows
        if not rows:
            self.vectorizer, self.matrix, self.emb_matrix = None, None, None
            return
        texts = [core_text(lang.norm(r["text"])) for r in rows]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english",
                                          token_pattern=lang.TOKEN_PATTERN)
        self.matrix = self.vectorizer.fit_transform(texts)
        self.emb_matrix = embed.embed(texts) if embed.available() else None
        embed.save_cache()

    def similar(self, text: str, k: int = 5, exclude_id: str | None = None, category: str | None = None,
                point: tuple | None = None):
        if self.vectorizer is None:
            return []
        core = core_text(lang.norm(text))
        sims = cosine_similarity(self.vectorizer.transform([core]), self.matrix)[0]
        if self.emb_matrix is not None:  # meaning-level match, works across languages
            sem = (self.emb_matrix @ embed.embed([core])[0] - EMB_FLOOR) / EMB_SPAN
            sims = np.maximum(sims, np.clip(sem, 0, 1))
        wording = sims  # before the location and category adjustments below
        if point and category:
            # an open case of the same category within 100 m is a candidate even when the wording shares
            # nothing (e.g. a Hinglish report of an incident first reported in Marathi)
            beside = np.array([r["category"] == category and r["status"] not in CLOSED_STATUSES
                               and r.get("geo_source") in geo.PRECISE
                               and geo.haversine_m(*point, r["lat"], r["lng"]) <= 100 for r in self.corpus_rows])
            sims = np.where(beside, np.maximum(sims, 0.35), sims)
        if category:  # semantic + category-aware re-ranking
            same = np.array([r["category"] == category for r in self.corpus_rows])
            sims = np.where(same, sims + 0.1, sims * 0.6)
        order = np.argsort(-sims)
        out = []
        for i in order:
            r = self.corpus_rows[i]
            if r["id"] == exclude_id:
                continue
            if sims[i] < SIM_FLOOR or len(out) >= k:
                break
            dist = None
            if point and r.get("geo_source") in geo.PRECISE:
                dist = round(geo.haversine_m(*point, r["lat"], r["lng"]))
            out.append({**r, "similarity": round(min(1.0, float(sims[i])), 3), "distance_m": dist,
                        "text_similarity": round(float(wording[i]), 3)})
        return out

    @staticmethod
    def cluster(similar: list[dict], category: str, ward: str | None):
        """Open same-category cases that are similar and near: within 500 m when both have GPS,
        otherwise in the same ward."""
        return [s for s in similar if s.get("category") == category and s.get("status") not in CLOSED_STATUSES
                and s["similarity"] >= SIM_CLUSTER
                and (s["distance_m"] <= CLUSTER_RADIUS_M if s["distance_m"] is not None else s.get("ward") == ward)]

    def open_matches(self, text: str, category: str, ward: str | None, point: tuple | None, exclude_id: str | None = None):
        """Candidates for 'is this the same real-world issue?' (discovery, joining and AI association)."""
        return self.cluster(self.similar(text, k=12, exclude_id=exclude_id, category=category, point=point), category, ward)

    # ---------------- components ----------------
    def classify(self, text: str, language: dict | None = None):
        # TF-IDF has no vocabulary outside its training languages, so it gets no vote there
        emb_only = bool(language) and language["support"] != "full"
        probs = train.predict_proba(self.model, [text], emb_only)[0]
        classes = self.model["tfidf"].classes_
        order = np.argsort(-probs)[:3]
        top = [{"category": str(classes[i]), "confidence": round(float(probs[i]), 3)} for i in order]
        return top

    @staticmethod
    def sentiment(text: str):
        words = WORD_RE.findall(lang.norm(text).lower())
        neg = pos = 0.0
        for i, w in enumerate(words):
            boost = 1.5 if i > 0 and words[i - 1] in INTENSIFIERS else 1.0
            if w in NEGATIVE_WORDS or (not w.isascii() and w.startswith(NEGATIVE_STEMS)):
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
        low = lang.norm(text).lower()
        ward = next((w for w in WARDS if w.lower() in low), None) or \
            next((w for alias, w in WARD_ALIASES.items() if lang.norm(alias) in low), None)
        days = None
        m = DURATION_RE.search(low)
        if m:
            n = int(m.group(1)) if m.group(1).isdigit() else next(v for k, v in NUM_WORDS.items() if lang.norm(k) == m.group(1))
            days = n * next(mult for units, mult in UNITS if re.match(lang.norm(units), m.group(2)))
        else:
            days = next((d for terms, d in FIXED_DURATIONS if any(lang.norm(t) in low for t in terms)), None)
        landmark = None
        for i, rx in enumerate(LANDMARK_RES):
            lm = rx.search(low)
            if lm:
                landmark = (lm.group(1) + " " + lm.group(2)).strip() if i == 0 else lm.group(1).strip()
                break
        urgency = sorted(_match(URGENCY_RES, low), key=lambda t: -URGENCY_TERMS[t])
        vulnerable = sorted(_match(VULNERABLE_RES, low))
        return {"ward": ward, "duration_days": days, "landmark": landmark,
                "urgency_terms": urgency, "vulnerable_groups": vulnerable}

    def priority(self, category: str, ents: dict, senti: dict, cluster_size: int, repeat: bool, by_gps: bool = False):
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
            where = f"within {CLUSTER_RADIUS_M} m" if by_gps else "in the same ward"
            factors.append({"factor": f"{cluster_size} similar open complaint(s) {where}", "points": round(min(15, 4 * cluster_size), 1)})
        if repeat:
            factors.append({"factor": "Repeat complaint / earlier ignored", "points": 6.0})
        score = round(min(100.0, sum(f["points"] for f in factors)), 1)
        level = "Critical" if score >= 60 else "High" if score >= 42 else "Medium" if score >= 25 else "Low"
        return score, level, factors

    # ---------------- recommendations ----------------
    def recommend(self, text: str, category: str, level: str, ents: dict, similar: list[dict]):
        # matched risk terms are appended in English so the rules below work for every language
        low = " ".join([text.lower(), *ents["urgency_terms"], *ents["vulnerable_groups"]])
        steps = list(CATEGORIES[category]["playbook"])
        # context-aware reordering: bubble up steps sharing words with the complaint
        kw = set(WORD_RE.findall(low))
        steps.sort(key=lambda s: -len(kw & set(WORD_RE.findall(s.lower()))))
        if level in ("Critical", "High"):
            steps.insert(0, "Escalate to ward officer and field team within 2 hours (high-risk case)")
        if ents["vulnerable_groups"]:
            steps.append("Inform citizen of interim safety measures for " + ", ".join(ents["vulnerable_groups"]))
        resolved = [s for s in similar if s.get("status") in ("Resolved", "Closed") and s.get("resolution_note")
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
        if category == "Garbage & Sanitation" and any(t in low for t in ("burning", "smoke")):
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
        sentences = [x for x in SENT_SPLIT.split(body) if len(x) > 8] or [body]
        core = sentences[0].strip()
        if len(core) > 80:
            cut = core[:80]
            core = cut[:cut.rfind(" ")].rstrip(" ,.") + "…"
        core = core.rstrip(" .।")
        core = core[0].upper() + core[1:] if core else category
        return core + (f" — {ward}" if ward and ward.lower() not in core.lower() else "")

    # ---------------- full pipeline ----------------
    def analyze(self, text: str, ward: str | None = None, exclude_id: str | None = None,
                point: tuple | None = None, category: str | None = None):
        """point: the complaint's own (lat, lng) when it has a real GPS fix or map pin.
        category: officer-corrected category, overrides the classifier."""
        language = lang.detect(text)
        top = self.classify(text, language)
        if category:
            top = [{"category": category, "confidence": 1.0}] + [t for t in top if t["category"] != category][:2]
        category = top[0]["category"]
        ents = self.entities(text)
        ward = ward or ents["ward"] or (geo.nearest_ward(*point) if point else None)
        senti = self.sentiment(text)
        similar = self.similar(text, k=12, exclude_id=exclude_id, category=category, point=point)
        # with GPS on both sides distance decides; otherwise fall back to "same ward"
        near = lambda s, radius: s["distance_m"] <= radius if s["distance_m"] is not None else s.get("ward") == ward
        cluster = self.cluster(similar, category, ward)
        duplicates = [s for s in cluster if near(s, DUPLICATE_RADIUS_M) and s["similarity"] >= (
            SIM_DUPLICATE if s["distance_m"] is None else 0.35 if s["distance_m"] <= 100 else 0.45)]
        low = lang.norm(text).lower()
        repeat = any(lang.norm(t) in low for t in REPEAT_TERMS)
        by_gps = bool(cluster) and all(s["distance_m"] is not None for s in cluster)
        score, level, factors = self.priority(category, ents, senti, len(cluster), repeat, by_gps)
        rec = self.recommend(text, category, level, ents, similar)
        # outside the fully supported languages the risk lexicon is blind, so a human must check
        needs_review = top[0]["confidence"] < 0.40 or language["support"] != "full"
        slim = lambda s: {k: s.get(k) for k in ("id", "title", "category", "ward", "status", "similarity", "distance_m",
                                                "resolution_note", "created_at")}
        return {
            "category": category,
            "confidence": top[0]["confidence"],
            "alternatives": top[1:],
            "needs_human_review": needs_review,
            "language": language,
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
