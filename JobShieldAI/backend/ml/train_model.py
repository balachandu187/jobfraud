"""
Model training pipeline.

Run once (never per request):
    python -m backend.ml.train_model
    python -m backend.ml.train_model --dataset data/jobs.csv --out saved_models

Pipeline
--------
1. Load the labelled dataset (title, company_profile, description, requirements,
   benefits, fraudulent).
2. Handle missing values — every text column is filled with "".
3. Split **by archetype** (`GroupShuffleSplit`). The dataset contains several paraphrase
   variants of each posting; a row-level split leaks near-duplicates into the test set
   and reports a meaningless 100%.
4. Fit the TF-IDF vectorizer on the training split only.
5. Train Logistic Regression with `class_weight='balanced'` for the class imbalance.
6. Wrap it in `CalibratedClassifierCV` so the reported probability is meaningful — it is
   blended directly into a user-facing risk score, so 0.7 should mean roughly 70%.
7. Report accuracy, precision, recall, F1 and the confusion matrix on the held-out split.
8. Persist vectorizer, model and metrics with Joblib.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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
from sklearn.model_selection import GroupShuffleSplit, train_test_split

TEXT_COLUMNS = ("title", "company_profile", "description", "requirements", "benefits")
RANDOM_STATE = 42
ALGORITHM = "TF-IDF (1,2)-grams + Calibrated Logistic Regression"


def prepare_text(frame: pd.DataFrame) -> pd.Series:
    """
    Builds the canonical single-string representation of a posting.

    The scan service builds text in the same order (title, company, description,
    metadata) so the vectorizer's vocabulary matches what inference feeds it.
    """
    data = frame.copy()
    for column in TEXT_COLUMNS:
        if column not in data.columns:
            data[column] = ""
        data[column] = data[column].fillna("").astype(str)
    return (
        data["title"] + " "
        + data["company_profile"] + " "
        + data["description"] + " "
        + data["requirements"] + " "
        + data["benefits"]
    ).str.strip()


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
    print("  Confusion matrix [[TN FP] [FN TP]]:")
    print(f"  {confusion_matrix(y_true, y_pred).tolist()}")
    return metrics


def train(
    dataset_path: Path,
    model_dir: Path,
    test_size: float = 0.30,
) -> Dict[str, Any]:
    """Trains, evaluates and persists the model. Returns the metrics dict."""
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Run `python data/create_dataset.py` to generate it."
        )

    print(f"[*] Loading dataset: {dataset_path}")
    frame = pd.read_csv(dataset_path)
    frame["company_profile"] = frame.get("company_profile", "").fillna("")
    labels = frame["fraudulent"].astype(int)
    features = prepare_text(frame)

    # ---- Split (grouped by archetype to avoid leakage) -------------------
    groups = frame["archetype"] if "archetype" in frame.columns else None
    if groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=RANDOM_STATE)
        train_idx, test_idx = next(splitter.split(features, labels, groups=groups))
    else:
        train_idx, test_idx = train_test_split(
            frame.index, test_size=test_size, random_state=RANDOM_STATE, stratify=labels
        )

    x_train, x_test = features.loc[train_idx], features.loc[test_idx]
    y_train, y_test = labels.loc[train_idx], labels.loc[test_idx]
    print(f"[*] Grouped split -> train {len(train_idx)} | held-out {len(test_idx)}")
    if groups is not None:
        print(
            f"[*] Archetypes -> train {groups.loc[train_idx].nunique()} | "
            f"held-out {groups.loc[test_idx].nunique()}"
        )

    # ---- Features (fit on train only) -----------------------------------
    vectorizer = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
        min_df=1,
    )
    print("[*] Fitting TF-IDF on the training split...")
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    # ---- Classifier ------------------------------------------------------
    print("[*] Training calibrated Logistic Regression...")
    base = LogisticRegression(
        C=1.0,
        max_iter=2000,
        random_state=RANDOM_STATE,
        class_weight="balanced",
        solver="liblinear",
    )
    folds = 5 if len(train_idx) >= 50 else 3
    model = CalibratedClassifierCV(base, method="sigmoid", cv=folds)
    model.fit(x_train_vec, y_train)

    # ---- Evaluate --------------------------------------------------------
    print("\n" + "=" * 60)
    print("MODEL EVALUATION — HELD-OUT POSTINGS (unseen archetypes)")
    print("=" * 60)
    y_pred = model.predict(x_test_vec)
    y_proba = model.predict_proba(x_test_vec)[:, 1]
    metrics = _evaluate("Held-out test set", y_test, y_pred, y_proba)
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine (0)", "Fraudulent (1)"],
                                zero_division=0))

    # In-sample numbers are printed only to expose overfitting, never as a claim.
    y_train_proba = model.predict_proba(x_train_vec)[:, 1]
    _evaluate("Training set (overfit check — NOT a performance claim)",
              y_train, model.predict(x_train_vec), y_train_proba)
    print("=" * 60)

    # ---- Persist ---------------------------------------------------------
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, model_dir / "tfidf_vectorizer.pkl")
    joblib.dump(model, model_dir / "model.pkl")
    joblib.dump(
        {
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "algorithm": ALGORITHM,
            "dataset_rows": int(len(frame)),
            "dataset_archetypes": int(groups.nunique()) if groups is not None else None,
            "split": "GroupShuffleSplit by archetype",
            "metrics": {key: round(float(value), 4) for key, value in metrics.items()},
            "text_columns": list(TEXT_COLUMNS),
        },
        model_dir / "model_metrics.pkl",
    )
    print(f"[SUCCESS] Artifacts written to {model_dir}")
    return metrics


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Train the JobShield AI fraud classifier.")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    from backend.config import settings

    try:
        train(args.dataset or settings.dataset_path, args.out or settings.model_dir)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
