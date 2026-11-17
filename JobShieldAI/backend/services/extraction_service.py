"""
Text extraction service: URL ingestion and screenshot OCR.

Both paths reduce an arbitrary input (a web page, an image) to the plain text that the
detection engines consume.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from backend.config import settings
from backend.core.security import UnsafeUrlError, guarded_get

logger = logging.getLogger(__name__)

STRIP_TAGS = ("script", "style", "noscript", "iframe", "svg", "nav", "footer", "header", "form")
CONTENT_SELECTORS = (
    "article", "main", "[role=main]", ".job-description", "#job-description",
    ".description", "#content", ".content",
)
MAX_TEXT_CHARS = 20_000


class ExtractionError(ValueError):
    """Raised when text cannot be extracted from the supplied source."""


def extract_readable_text(html: str) -> str:
    """Reduces an HTML document to the most posting-like readable text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(list(STRIP_TAGS)):
        tag.decompose()

    container = None
    for selector in CONTENT_SELECTORS:
        candidate = soup.select_one(selector)
        if candidate and len(candidate.get_text(" ", strip=True)) > 200:
            container = candidate
            break

    root = container or soup.body or soup
    lines: List[str] = []
    for line in root.get_text("\n", strip=True).splitlines():
        cleaned = " ".join(line.split())
        if cleaned and (not lines or lines[-1] != cleaned):
            lines.append(cleaned)

    return "\n".join(lines)[:MAX_TEXT_CHARS].strip()


class ExtractionService:
    """Turns a URL or an uploaded image into analysable text."""

    def from_url(self, url: str) -> Dict[str, Any]:
        try:
            fetched = guarded_get(url)
        except UnsafeUrlError as exc:
            raise ExtractionError(str(exc)) from exc

        html = fetched["html"]
        soup = BeautifulSoup(html, "html.parser")
        page_title = (soup.title.get_text(strip=True) if soup.title else "")[:300]
        text = extract_readable_text(html)

        if len(text) < 40:
            raise ExtractionError(
                "The page loaded but contained almost no readable text. It may require a "
                "login or render entirely with JavaScript — paste the text instead."
            )

        return {
            "source_type": "url",
            "requested_url": url,
            "resolved_url": fetched["url"],
            "page_title": page_title,
            "text": text,
            "characters": len(text),
        }

    def from_image(self, content: bytes, language: str = "eng") -> Dict[str, Any]:
        if len(content) > settings.max_upload_bytes:
            raise ExtractionError(
                f"Screenshot exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
            )
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:  # optional dependency
            raise ExtractionError(
                "OCR support is not installed. Run `pip install pillow pytesseract` and "
                "install the Tesseract binary for your platform."
            ) from exc

        try:
            image = Image.open(io.BytesIO(content))
        except Exception as exc:
            raise ExtractionError("Uploaded file is not a readable image.") from exc

        try:
            text = pytesseract.image_to_string(image, lang=language)
        except pytesseract.TesseractNotFoundError as exc:
            raise ExtractionError(
                "Tesseract OCR binary not found on PATH. Install it from "
                "https://github.com/tesseract-ocr/tesseract and retry."
            ) from exc
        except Exception as exc:
            raise ExtractionError(f"OCR failed: {exc}") from exc

        text = (text or "").strip()
        if not text:
            raise ExtractionError(
                "OCR produced no readable text. Try a higher-resolution screenshot."
            )

        return {
            "source_type": "image",
            "text": text,
            "characters": len(text),
            "image_size": f"{image.width}x{image.height}",
        }


_service: ExtractionService | None = None


def get_extraction_service() -> ExtractionService:
    global _service
    if _service is None:
        _service = ExtractionService()
    return _service
