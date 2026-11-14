"""
Model Training Pipeline for JobShield AI
Extracts TF-IDF features from text fields and trains a calibrated Logistic Regression
classifier to detect fraudulent job postings.
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

def prepare_text_features(df: pd.DataFrame) -> pd.Series:
    """Combines all text columns into a single consolidated string for NLP."""
    text_cols = ["title", "company_profile", "description", "requirements", "benefits"]
    # Fill missing values with empty string
    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("")
            
    combined = (
        df["title"] + " " +
        df["company_profile"] + " " +
        df["description"] + " " +
        df["requirements"] + " " +
        df["benefits"]
    )
    return combined

def train_and_evaluate(data_path: str = "data/jobs.csv", model_dir: str = "saved_models"):
    """Loads dataset, splits data, trains TF-IDF + Logistic Regression, and persists artifacts."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Run data/create_dataset.py first.")

    print(f"[*] Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    
    X_text = prepare_text_features(df)
    y = df["fraudulent"].astype(int)

    # Train / Test split (80% train, 20% test) with stratified sampling
    X_train_text, X_test_text, y_train, y_test = train_test_split(
        X_text, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"[*] Training samples: {len(X_train_text)} | Testing samples: {len(X_test_text)}")

    # Feature extraction with TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True
    )
    
    print("[*] Extracting TF-IDF n-gram features...")
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_test_vec = vectorizer.transform(X_test_text)

    # Logistic Regression Classifier
    print("[*] Training Logistic Regression model...")
    model = LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42,
        class_weight="balanced"
    )
    model.fit(X_train_vec, y_train)

    # Predictions & Evaluation
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "="*50)
    print("MODEL EVALUATION RESULTS")
    print("="*50)
    print(f"Accuracy: {acc * 100:.2f}%")
    print(f"F1-Score: {f1 * 100:.2f}%")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine (0)", "Fraudulent (1)"]))
    print("="*50)

    # Save artifacts
    os.makedirs(model_dir, exist_ok=True)
    vec_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
    model_path = os.path.join(model_dir, "model.pkl")
    
    joblib.dump(vectorizer, vec_path)
    joblib.dump(model, model_path)
    print(f"\n[SUCCESS] Model and Vectorizer saved to '{model_dir}' directory.")
    
    return acc, f1

if __name__ == "__main__":
    train_and_evaluate()

