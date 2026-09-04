"""Train and evaluate a context-aware cyberbullying model candidate.

The script never overwrites the live model files. It writes candidate files
only after evaluating both the current live model and the new model on the
same stratified holdout set.
"""

from pathlib import Path
import json
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

from utils import clean_text


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR.parent / "cyberbullying-backend-v2" / "data" / "cyberbullying.csv"
MODEL_OUT = BASE_DIR / "cyberbullying_model_candidate.pkl"
VECTORIZER_OUT = BASE_DIR / "tfidf_vectorizer_candidate.pkl"
REPORT_OUT = BASE_DIR / "model_candidate_report.json"

TEXT_COLUMN = "Text"
LABEL_COLUMN = "oh_label"
RANDOM_STATE = 42

CONTEXT_TESTS = [
    ("You did a great job on this project.", 0),
    ("I disagree with you, but I respect your opinion.", 0),
    ("I hate this video, but I do not hate you.", 0),
    ("That was a dumb mistake; please be more careful next time.", 0),
    ("You are stupid and nobody likes you.", 1),
    ("Shut up, idiot. You are such a loser.", 1),
]


def metrics(y_true, y_pred):
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def context_results(model, vectorizer):
    cleaned = [clean_text(text) for text, _ in CONTEXT_TESTS]
    probabilities = model.predict_proba(vectorizer.transform(cleaned))[:, 1]
    results = []
    for (text, expected), probability in zip(CONTEXT_TESTS, probabilities):
        predicted = int(probability >= 0.5)
        results.append({
            "text": text,
            "expected": expected,
            "predicted": predicted,
            "bullying_probability": round(float(probability), 4),
            "correct": predicted == expected,
        })
    return results


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    print(f"Loading {DATASET_PATH}")
    frame = pd.read_csv(DATASET_PATH, usecols=[TEXT_COLUMN, LABEL_COLUMN]).dropna()
    texts = frame[TEXT_COLUMN].map(clean_text)
    labels = frame[LABEL_COLUMN].astype(int)

    train_text, test_text, train_labels, test_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    print("Evaluating current live model...")
    with open(BASE_DIR / "cyberbullying_model.pkl", "rb") as handle:
        current_model = pickle.load(handle)
    with open(BASE_DIR / "tfidf_vectorizer.pkl", "rb") as handle:
        current_vectorizer = pickle.load(handle)
    current_predictions = current_model.predict(current_vectorizer.transform(test_text))

    print("Training bigram candidate...")
    candidate_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=40000,
        min_df=2,
        max_df=0.98,
        sublinear_tf=True,
        strip_accents="unicode",
    )
    train_vectors = candidate_vectorizer.fit_transform(train_text)
    test_vectors = candidate_vectorizer.transform(test_text)
    candidate_model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    candidate_model.fit(train_vectors, train_labels)
    candidate_predictions = candidate_model.predict(test_vectors)

    report = {
        "dataset_rows": int(len(frame)),
        "label_counts": {str(k): int(v) for k, v in labels.value_counts().sort_index().items()},
        "current": {
            "metrics": metrics(test_labels, current_predictions),
            "context_tests": context_results(current_model, current_vectorizer),
        },
        "candidate": {
            "metrics": metrics(test_labels, candidate_predictions),
            "context_tests": context_results(candidate_model, candidate_vectorizer),
            "vectorizer": {
                "ngram_range": [1, 2],
                "max_features": 40000,
                "min_df": 2,
                "max_df": 0.98,
                "sublinear_tf": True,
            },
        },
    }

    with open(MODEL_OUT, "wb") as handle:
        pickle.dump(candidate_model, handle)
    with open(VECTORIZER_OUT, "wb") as handle:
        pickle.dump(candidate_vectorizer, handle)
    REPORT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Candidate model: {MODEL_OUT}")
    print(f"Candidate vectorizer: {VECTORIZER_OUT}")
    print(f"Report: {REPORT_OUT}")


if __name__ == "__main__":
    main()
