"""Train the grievance category classifier.

Run:  python -m app.ml.train
Outputs: models/classifier.joblib, models/metrics.json

The model is two classifiers whose probabilities are averaged:
  tfidf - word + char n-grams -> Logistic Regression (strong on Hinglish and typos)
  emb   - multilingual sentence embeddings -> Logistic Regression (meaning, any script)
Training rows are the synthetic templates plus every complaint whose category an
officer has confirmed or corrected in the console (real text, weighted up).
"""
import json
import sqlite3
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from app import lang
from app.ml import embed
from app.ml.dataset import generate_training
from app.ml.evalset import DEV, FINAL, HI_FINAL, MR_FINAL, PROBE

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
VERIFIED_WEIGHT = 10.0  # one officer-verified complaint counts as much as ten synthetic rows

# Older hand-written check set. Templates were later written to cover these, so it
# counts as development data together with evalset.DEV.
HOLDOUT = [
    ("Since Sunday our taps are dry and the society is buying water cans", "Water Supply"),
    ("The tap water smells like sewage and my kids fell ill", "Water Supply"),
    ("A crater-like hole has formed on the highway service road, bikers keep skidding", "Roads & Potholes"),
    ("The tar road near our apartment has washed away in rain", "Roads & Potholes"),
    ("Our whole building has been without power since morning and inverter is dead", "Electricity"),
    ("Transformer near the chowk made a loud blast and smoke is coming", "Electricity"),
    ("Rubbish heap near the corner has not been picked up and rats everywhere", "Garbage & Sanitation"),
    ("Sweepers have not cleaned our street for many days", "Garbage & Sanitation"),
    ("Black stinking water is overflowing from the gutter line into our lane", "Drainage & Sewage"),
    ("Manhole lid missing on the main road, a cow fell inside", "Drainage & Sewage"),
    ("It is pitch dark on our street at night as the lamps are dead", "Street Lights"),
    ("Pole light near the temple has been off for a week", "Street Lights"),
    ("Several neighbours have high fever and platelet counts are dropping", "Public Health"),
    ("Mosquitoes everywhere and two kids admitted with dengue", "Public Health"),
    ("The PMPML bus skipped our stop again and we were late to office", "Public Transport"),
    ("The driver of the city bus was talking on phone while driving", "Public Transport"),
    ("Vendors have occupied the entire footpath so pedestrians walk on the road", "Encroachment"),
    ("A builder has fenced off the public playground", "Encroachment"),
    ("Some boys are passing lewd comments at girls near the tuition class", "Safety & Law"),
    ("Two bikes were stolen from our parking last night", "Safety & Law"),
    ("A huge gulmohar tree collapsed on parked cars during the storm", "Tree & Parks"),
    ("The children's slide in the garden is rusted and broken", "Tree & Parks"),
]


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, stop_words="english",
                                 token_pattern=lang.TOKEN_PATTERN)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
    ])
    return Pipeline([("features", features),
                     ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced"))])


def fit(X, y, weights=None) -> dict:
    """Both classifiers. `emb` is None when the embedding model is unavailable."""
    X = [lang.norm(t) for t in X]
    model = {"tfidf": build_pipeline().fit(X, y, clf__sample_weight=weights), "emb": None, "embed_model": None}
    if embed.available():
        # C=1 was picked on the development set (HOLDOUT + DEV), not on any final set
        model["emb"] = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced").fit(
            embed.embed(X), y, sample_weight=weights)
        model["embed_model"] = embed.MODEL
    return model


def predict_proba(model: dict, texts, emb_only: bool = False):
    texts = [lang.norm(t) for t in texts]
    probs = model["tfidf"].predict_proba(texts)
    if model["emb"] is not None:
        sem = model["emb"].predict_proba(embed.embed(texts))
        probs = sem if emb_only else (probs + sem) / 2
    return probs


def _score(model, rows, gate: float = 0.40, emb_only: bool = False):
    """Accuracy on hand-written rows, plus how many pass the auto-routing confidence gate."""
    probs = predict_proba(model, [t for t, _ in rows], emb_only)
    classes = model["tfidf"].classes_
    pred = [(classes[p.argmax()], float(p.max())) for p in probs]
    errors = [{"text": t, "true": a, "pred": str(c), "confidence": round(conf, 3)}
              for (t, a), (c, conf) in zip(rows, pred) if a != c]
    return {"size": len(rows), "accuracy": round(1 - len(errors) / len(rows), 4),
            "auto_routed": sum(conf >= gate for _, conf in pred),
            "auto_routed_wrong": sum(e["confidence"] >= gate for e in errors), "errors": errors}


def verified_rows():
    """Real complaints whose category an officer confirmed or corrected in the console."""
    from app import db
    try:
        with db.conn() as c:
            return [(r["text"], r["category"]) for r in
                    c.execute("SELECT text, category FROM grievances WHERE label_source='officer'")]
    except sqlite3.OperationalError:  # database not created yet
        return []


def main():
    rows = generate_training()
    X, y = [r[0] for r in rows], [r[1] for r in rows]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model = fit(Xtr, ytr)
    pred = model["tfidf"].classes_[predict_proba(model, Xte).argmax(1)]
    dev = _score(model, HOLDOUT + DEV)
    final = _score(model, FINAL)
    brief = lambda s: {k: s[k] for k in ("size", "accuracy", "auto_routed", "auto_routed_wrong")}
    metrics = {
        "train_size": len(Xtr), "test_size": len(Xte), "classes": sorted(set(y)),
        "embeddings": model["emb"] is not None, "embed_model": model["embed_model"],
        "test_accuracy": round(accuracy_score(yte, pred), 4),
        "test_macro_f1": round(f1_score(yte, pred, average="macro"), 4),
        # complaints written after the templates were frozen: the honest number
        "holdout_accuracy": final["accuracy"], "holdout_size": final["size"],
        "holdout_auto_routed": final["auto_routed"], "holdout_auto_routed_wrong": final["auto_routed_wrong"],
        "holdout_errors": final["errors"],
        "holdout_accuracy_tfidf_only": _score({**model, "emb": None}, FINAL)["accuracy"],
        # complaints known while writing templates: optimistic
        "dev_accuracy": dev["accuracy"], "dev_size": dev["size"],
        # Devanagari sets: optimistic like dev (see evalset.py); zero_shot below is the clean number
        "languages": {"Hindi": _score(model, HI_FINAL), "Marathi": _score(model, MR_FINAL)},
        "report": classification_report(yte, pred, output_dict=True),
    }
    if model["emb"] is not None:
        # same embedding classifier trained without a single Devanagari row
        latin = [(t, c) for t, c in zip(Xtr, ytr) if not lang.DEV_RE.search(t)]
        zero = {**fit(*zip(*latin)), "tfidf": model["tfidf"]}
        metrics["zero_shot"] = {"Hindi": brief(_score(zero, HI_FINAL, emb_only=True)),
                                "Marathi": brief(_score(zero, MR_FINAL, emb_only=True))}
        # languages with no template and no lexicon: embeddings only
        metrics["probe"] = {name: brief(_score(model, rs, emb_only=True)) for name, rs in PROBE.items()}
    # final model on all synthetic data + officer-verified real complaints
    # (no hand-written evaluation complaint is trained on)
    real = verified_rows()
    metrics["verified_rows"] = len(real)
    weights = np.array([1.0] * len(X) + [VERIFIED_WEIGHT] * len(real))
    final_model = fit(X + [t for t, _ in real], y + [c for _, c in real], weights)
    embed.save_cache(min_new=1)
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(final_model, MODEL_DIR / "classifier.joblib")
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"test acc={metrics['test_accuracy']} macroF1={metrics['test_macro_f1']} dev acc={metrics['dev_accuracy']} "
          f"final acc={metrics['holdout_accuracy']} ({len(metrics['holdout_errors'])} errors, "
          f"{metrics['holdout_auto_routed_wrong']} of them auto-routed), tf-idf only {metrics['holdout_accuracy_tfidf_only']}")
    for name, s in metrics["languages"].items():
        print(f"{name}: {s['accuracy']} ({s['auto_routed_wrong']} wrong auto-routed)", metrics.get("zero_shot", {}).get(name))
    print("probe:", metrics.get("probe"), "| officer-verified rows in training:", len(real))
    return metrics


if __name__ == "__main__":
    main()
