"""Train and evaluate the deployable v3 word+character cyberbullying model.

Candidate artifacts are written separately. The live model is never overwritten
by this script, so promotion remains an explicit, reviewed step.
"""

from pathlib import Path
import json
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

from utils import clean_text

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR.parent / "cyberbullying-backend-v2" / "data" / "cyberbullying.csv"
MODEL_OUT = BASE_DIR / "cyberbullying_model_candidate.pkl"
VECTORIZER_OUT = BASE_DIR / "tfidf_vectorizer_candidate.pkl"
REPORT_OUT = BASE_DIR / "model_candidate_report.json"
THRESHOLD = 0.40
RANDOM_STATE = 42

CONTEXT_TESTS = [
    ("You did a great job on this project.", 0),
    ("I disagree with you, but I respect your opinion.", 0),
    ("I hate this video, but I do not hate you.", 0),
    ("That was a dumb mistake; please be more careful next time.", 0),
    ("You are stupid and nobody likes you.", 1),
    ("Shut up, idiot. You are such a loser.", 1),
    ("You are stuuupid and a l0ser.", 1),
]


def build_vectorizer():
    return FeatureUnion([
        ("word", TfidfVectorizer(
            ngram_range=(1, 2), max_features=25000, min_df=2,
            max_df=0.995, sublinear_tf=True, strip_accents="unicode",
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), max_features=25000,
            min_df=3, sublinear_tf=True,
        )),
    ])


def metrics(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_true, predictions)), 4),
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_true, predictions).tolist(),
    }


def context_results(model, vectorizer, threshold):
    texts = [clean_text(text) for text, _ in CONTEXT_TESTS]
    probabilities = model.predict_proba(vectorizer.transform(texts))[:, 1]
    return [
        {
            "text": text,
            "expected": expected,
            "predicted": int(probability >= threshold),
            "bullying_probability": round(float(probability), 4),
            "correct": int(probability >= threshold) == expected,
        }
        for (text, expected), probability in zip(CONTEXT_TESTS, probabilities)
    ]


def main():
    frame = pd.read_csv(DATASET_PATH, usecols=["Text", "oh_label"]).dropna()
    texts = frame["Text"].map(clean_text)
    labels = frame["oh_label"].astype(int)
    train_text, test_text, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_STATE, stratify=labels,
    )

    with open(BASE_DIR / "cyberbullying_model.pkl", "rb") as handle:
        current_model = pickle.load(handle)
    with open(BASE_DIR / "tfidf_vectorizer.pkl", "rb") as handle:
        current_vectorizer = pickle.load(handle)
    current_probabilities = current_model.predict_proba(
        current_vectorizer.transform(test_text)
    )[:, 1]

    candidate_vectorizer = build_vectorizer()
    train_vectors = candidate_vectorizer.fit_transform(train_text)
    candidate_model = LogisticRegression(
        max_iter=1000, C=2.0, class_weight={0: 1, 1: 1.3},
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    candidate_model.fit(train_vectors, train_labels)
    candidate_probabilities = candidate_model.predict_proba(
        candidate_vectorizer.transform(test_text)
    )[:, 1]

    report = {
        "model_version": "hybrid-word-char-rules-v3.0",
        "dataset_rows": int(len(frame)),
        "label_counts": {str(k): int(v) for k, v in labels.value_counts().sort_index().items()},
        "decision_threshold": THRESHOLD,
        "current": {
            "metrics": metrics(test_labels, current_probabilities, 0.5),
            "context_tests": context_results(current_model, current_vectorizer, 0.5),
        },
        "candidate": {
            "metrics": metrics(test_labels, candidate_probabilities, THRESHOLD),
            "context_tests": context_results(candidate_model, candidate_vectorizer, THRESHOLD),
            "features": ["word_tfidf_1_2", "character_tfidf_3_5"],
            "class_weight": {"safe": 1.0, "harmful": 1.3},
        },
    }

    with open(MODEL_OUT, "wb") as handle:
        pickle.dump(candidate_model, handle)
    with open(VECTORIZER_OUT, "wb") as handle:
        pickle.dump(candidate_vectorizer, handle)
    REPORT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
