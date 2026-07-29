"""
compare_models.py - Train and compare multiple ML models on your dataset.

This trains Logistic Regression (your current model), Multinomial Naive Bayes,
Linear SVM, and Random Forest on the same TF-IDF features, then prints a
comparison table of Accuracy / Precision / Recall / F1-score for each.

Use the resulting table directly in Chapter 5 of your report to justify why
Logistic Regression was chosen (or to argue for switching to a better model).

USAGE:
1. Edit CSV_PATH, TEXT_COLUMN, LABEL_COLUMN below to match your dataset.
2. Run: python3 compare_models.py
"""

import re
import string
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# ---- EDIT THESE THREE LINES TO MATCH YOUR DATASET ----
CSV_PATH = "your_dataset.csv"
TEXT_COLUMN = "text"
LABEL_COLUMN = "label"
# --------------------------------------------------------


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


print(f"Loading dataset from {CSV_PATH} ...")
df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=[TEXT_COLUMN, LABEL_COLUMN])

X_text = df[TEXT_COLUMN].apply(clean_text)
y = df[LABEL_COLUMN]

X_train, X_test, y_train, y_test = train_test_split(
    X_text, y, test_size=0.2, random_state=42, stratify=y
)

print("Fitting shared TF-IDF vectorizer...")
vectorizer = TfidfVectorizer(max_features=5000)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Multinomial Naive Bayes": MultinomialNB(),
    "Linear SVM": LinearSVC(),
    "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
}

results = []

for name, clf in models.items():
    print(f"Training {name}...")
    clf.fit(X_train_vec, y_train)
    y_pred = clf.predict(X_test_vec)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    results.append({
        "Model": name,
        "Accuracy": round(acc * 100, 2),
        "Precision": round(prec * 100, 2),
        "Recall": round(rec * 100, 2),
        "F1-score": round(f1 * 100, 2),
    })

results_df = pd.DataFrame(results).sort_values("F1-score", ascending=False)

print("\n===== MODEL COMPARISON (values in %) =====")
print(results_df.to_string(index=False))

results_df.to_csv("model_comparison.csv", index=False)
print("\nSaved to model_comparison.csv -- copy this table into Chapter 5 of your report.")