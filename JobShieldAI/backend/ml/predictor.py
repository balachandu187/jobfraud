"""
Standalone predictor.

`backend.services.ml_service.MLService` is the class the API uses (it adds metadata
and health reporting). This thin wrapper exists so the model can be exercised from a
script or notebook without starting the app:

    python -m backend.ml.predictor "text of a job advertisement"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from backend.services.ml_service import MLService


class Predictor:
    """Minimal facade over MLService for offline use."""

    def __init__(self, model_dir: Optional[str] = None) -> None:
        self.service = MLService(model_dir=model_dir)

    @property
    def is_ready(self) -> bool:
        return self.service.is_ready

    def predict(self, text: str) -> Dict[str, Any]:
        return self.service.predict(text)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a single prediction.")
    parser.add_argument("text", nargs="?", help="Advertisement text; reads stdin if omitted")
    parser.add_argument("--model-dir", default=None)
    args = parser.parse_args(argv)

    text = args.text or sys.stdin.read()
    if not text.strip():
        print("[ERROR] No text supplied.", file=sys.stderr)
        return 2

    predictor = Predictor(model_dir=args.model_dir)
    if not predictor.is_ready:
        print(f"[ERROR] Model unavailable: {predictor.service.load_error}", file=sys.stderr)
        print("        Train it with: python -m backend.ml.train_model", file=sys.stderr)
        return 1

    print(json.dumps(predictor.predict(text), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
