"""
Model Training Pipeline for JobShield AI
Extracts TF-IDF features from text fields and trains a calibrated Logistic Regression
classifier to detect fraudulent job postings.

Key correctness properties
--------------------------
1. Grouped train/test split. The dataset contains several paraphrase variants of each
   job archetype. Splitting rows at random leaks near-duplicate text across the split
   and produces a meaningless 100% score. We split by `archetype` so the held-out set
   contains postings the model has never seen in any form.
2. The vectorizer is fit on the training split only, never on the test split.
3. The vectorizer must be fed the *same* aggregated text shape at inference time as at
   training time. `prepare_text` is the single shared definition of that shape and is
   imported by both the trainer and the predictor (`model/predictor.py`), so the two
   can never drift apart.
4. Probability calibration is applied (CalibratedClassifierCV, sigmoid) so that a
   reported "70% fraud probability" actually means roughly 70%, which matters because
   the risk engine blends that number directly into a user-facing score.
"""

import os
import sys
from typing import Dict, Tuple

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

TEXT_COLUMNS = ("title", "company_profile", "description", "requirements", "benefits")
RANDOM_STATE = 42


def prepare_text(df: pd.DataFrame) -> pd.Series:
    """
    Builds the canonical single-string representation of a posting.

    This exact column order and separator are used by `JobPredictor.predict`, so the
    TF-IDF vocabulary learned here matches what production inference feeds the model.
    """
    frame = df.copy()
    for column in TEXT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    return (
        frame["title"] + " "
        + frame["company_profile"] + " "
        + frame["description"] + " "
        + frame["requirements"] + " "
        + frame["benefits"]
    ).str.strip()


# Backwards-compatible alias for older callers/tests.
prepare_text_features = prepare_text


def _evaluate(name: str, y_true, y_pred, y_proba) -> Dict[str, float]:
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_proba),
    }
    print(f"\n[{name}]")
    print(f"  Accuracy : {metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision: {metrics['precision'] * 100:.2f}%")
    print(f"  Recall   : {metrics['recall'] * 100:.2f}%   <- most important: missed scams")
    print(f"  F1-Score : {metrics['f1'] * 100:.2f}%")
    print(f"  ROC-AUC  : {metrics['roc_auc']:.3f}")
    print("  Confusion Matrix [[TN FP] [FN TP]]:")
    print(f"  {confusion_matrix(y_true, y_pred).tolist()}")
    return metrics


def train_and_evaluate(data_path: str = "data/jobs.csv", model_dir: str = "saved_models") -> Dict[str, float]:
    """Loads the dataset, trains TF-IDF + calibrated Logistic Regression, persists artifacts."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Run data/create_dataset.py first.")

    print(f"[*] Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    df[TEXT_COLUMNS[1]] = df.get("company_profile", "").fillna("")
    y = df["fraudulent"].astype(int)
    X_text = prepare_text(df)

    # ---- Leak-free split -------------------------------------------------
    groups = df["archetype"] if "archetype" in df.columns else None
    if groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_STATE)
        train_idx, test_idx = next(splitter.split(X_text, y, groups=groups))
    else:
        from sklearn.model_selection import train_test_split
        train_idx, test_idx = train_test_split(
            df.index, test_size=0.30, random_state=RANDOM_STATE, stratify=y
        )

    X_train_text, X_test_text = X_text.loc[train_idx], X_text.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]
    print(f"[*] Grouped split -> training rows: {len(train_idx)} | held-out rows: {len(test_idx)}")
    if groups is not None:
        print(f"[*] Archetypes -> train: {groups.loc[train_idx].nunique()} | held-out: {groups.loc[test_idx].nunique()}")

    # ---- Features --------------------------------------------------------
    vectorizer = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
        min_df=1,
    )
    print("[*] Extracting TF-IDF n-gram features (fit on training split only)...")
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_test_vec = vectorizer.transform(X_test_text)

    # ---- Classifier ------------------------------------------------------
    print("[*] Training calibrated Logistic Regression model...")
    base_model = LogisticRegression(
        C=1.0,
        max_iter=2000,
        random_state=RANDOM_STATE,
        class_weight="balanced",
        solver="liblinear",
    )
    # Shrink the calibration folds if the training split is small.
    cv_folds = 5 if len(train_idx) >= 50 else 3
    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=cv_folds)
    model.fit(X_train_vec, y_train)

    # ---- Evaluation ------------------------------------------------------
    y_pred = model.predict(X_test_vec)
    y_proba = model.predict_proba(X_test_vec)[:, 1]

    print("\n" + "=" * 58)
    print("MODEL EVALUATION — HELD-OUT POSTINGS (unseen archetypes)")
    print("=" * 58)
    metrics = _evaluate("Held-out test set", y_test, y_pred, y_proba)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine (0)", "Fraudulent (1)"], zero_division=0))

    # In-sample numbers are reported only to expose overfitting, never as a claim.
    y_train_pred = model.predict(X_train_vec)
    y_train_proba = model.predict_proba(X_train_vec)[:, 1]
    _evaluate("Training set (overfit check, NOT a performance claim)", y_train, y_train_pred, y_train_proba)
    print("=" * 58)

    # ---- Persist ---------------------------------------------------------
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(vectorizer, os.path.join(model_dir, "tfidf_vectorizer.pkl"))
    joblib.dump(model, os.path.join(model_dir, "model.pkl"))
    joblib.dump(
        {
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "dataset_rows": int(len(df)),
            "dataset_archetypes": int(groups.nunique()) if groups is not None else None,
            "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
            "text_columns": list(TEXT_COLUMNS),
        },
        os.path.join(model_dir, "model_metrics.pkl"),
    )
    print(f"[SUCCESS] Model, vectorizer and metrics saved to '{model_dir}'.")

    return metrics


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    train_and_evaluate()
