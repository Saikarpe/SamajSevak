"""Train the grievance category classifier.

Run:  python -m app.ml.train
Outputs: models/classifier.joblib, models/metrics.json
"""
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ml.dataset import generate_training

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"

# Hand-written, template-free complaints to check real-world generalisation
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
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, stop_words="english")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
    ])
    return Pipeline([("features", features),
                     ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced"))])


def main():
    rows = generate_training()
    X, y = [r[0] for r in rows], [r[1] for r in rows]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    pipe = build_pipeline().fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    hx, hy = [h[0] for h in HOLDOUT], [h[1] for h in HOLDOUT]
    hpred = pipe.predict(hx)
    metrics = {
        "train_size": len(Xtr), "test_size": len(Xte), "classes": sorted(set(y)),
        "test_accuracy": round(accuracy_score(yte, pred), 4),
        "test_macro_f1": round(f1_score(yte, pred, average="macro"), 4),
        "holdout_accuracy": round(accuracy_score(hy, hpred), 4),
        "holdout_size": len(HOLDOUT),
        "holdout_errors": [{"text": t, "true": a, "pred": p} for t, a, p in zip(hx, hy, hpred) if a != p],
        "report": classification_report(yte, pred, output_dict=True),
    }
    # final model on all synthetic data + holdout-free
    final = build_pipeline().fit(X, y)
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(final, MODEL_DIR / "classifier.joblib")
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"test acc={metrics['test_accuracy']} macroF1={metrics['test_macro_f1']} "
          f"holdout acc={metrics['holdout_accuracy']} ({len(metrics['holdout_errors'])} errors)")
    for e in metrics["holdout_errors"]:
        print("  ", e)


if __name__ == "__main__":
    main()
