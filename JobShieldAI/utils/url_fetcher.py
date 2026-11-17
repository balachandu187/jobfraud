"""
Safe URL text extraction for JobShield AI.

Job advertisements arrive as links (LinkedIn posts, Telegram forwards, look-alike
career portals). This module fetches a page and reduces it to the readable posting
text that the detection engines consume.

Security posture
----------------
* Only http/https schemes are permitted.
* Hostnames that resolve to private, loopback, link-local or otherwise reserved
  address space are rejected, which blocks SSRF attempts such as
  ``http://localhost:8000/api/history`` or ``http://169.254.169.254/``.
* Redirects are followed manually so every hop is re-validated against the same policy.
* Response size and total wall-clock time are bounded.
* Nothing is executed: parsing uses BeautifulSoup with the stdlib HTML parser.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (compatible; JobShieldAI/2.0; +https://github.com/balachandu187/jobfraud) "
    "Python-requests"
)
MAX_BYTES = 2_000_000          # 2 MB response cap
MAX_REDIRECTS = 4
TIMEOUT_SECONDS = 10
MAX_TEXT_CHARS = 20_000

#: Trust store resolution order: explicit override, then the OS bundle, then certifi.
#: (Slim container images sometimes ship a stale certifi bundle, so the OS path wins.)
_CA_CANDIDATES = (
    os.environ.get("JOBSHIELD_CA_BUNDLE"),
    "/etc/ssl/certs/ca-certificates.crt",
)


def _ca_bundle() -> Optional[str]:
    """Returns an existing CA bundle path, or None to let requests use its default."""
    for candidate in _CA_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None

#: Elements that never carry posting content.
STRIP_TAGS = ("script", "style", "noscript", "iframe", "svg", "nav", "footer", "header", "form")
#: Containers likely to hold the actual posting, checked in priority order.
CONTENT_SELECTORS = (
    "article",
    "main",
    "[role=main]",
    ".job-description",
    "#job-description",
    ".description",
    "#content",
    ".content",
)


class UrlFetchError(ValueError):
    """Raised when a URL cannot be fetched or yields no usable text."""


def _is_public_host(hostname: str) -> bool:
    """True when every resolved address for `hostname` is public."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UrlFetchError(f"Could not resolve host '{hostname}'.") from exc

    if not infos:
        raise UrlFetchError(f"Could not resolve host '{hostname}'.")

    for info in infos:
        raw = info[4][0]
        try:
            address = ipaddress.ip_address(raw.split("%")[0])
        except ValueError:
            continue
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            return False
    return True


def _validate_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        raise UrlFetchError("Only http and https URLs can be analysed.")
    if not parsed.hostname:
        raise UrlFetchError("That URL has no host name.")
    if not _is_public_host(parsed.hostname):
        raise UrlFetchError(
            "Refusing to fetch a private or loopback address. "
            "Paste the advertisement text directly instead."
        )
    return parsed.geturl()


def _fetch(url: str) -> tuple[str, str]:
    """Fetches `url`, validating every redirect hop. Returns (final_url, html)."""
    current = _validate_url(url)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})

    verify = _ca_bundle() or True

    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = session.get(
                current,
                timeout=TIMEOUT_SECONDS,
                stream=True,
                allow_redirects=False,
                headers={"Accept": "text/html,application/xhtml+xml"},
                verify=verify,
            )
        except requests.exceptions.SSLError as exc:
            raise UrlFetchError(
                "TLS certificate verification failed for that host. If you are behind a "
                "corporate proxy, set JOBSHIELD_CA_BUNDLE to your organisation's CA file."
            ) from exc
        except requests.exceptions.ConnectTimeout as exc:
            raise UrlFetchError("The host timed out while connecting.") from exc
        except requests.exceptions.ReadTimeout as exc:
            raise UrlFetchError("The host took too long to respond.") from exc
        except requests.exceptions.TooManyRedirects as exc:
            raise UrlFetchError("Too many redirects.") from exc
        except requests.exceptions.RequestException as exc:
            raise UrlFetchError(f"Could not reach that URL ({type(exc).__name__}).") from exc

        if response.is_redirect:
            location = response.headers.get("Location", "")
            response.close()
            if not location:
                raise UrlFetchError("Server redirected without a target location.")
            current = _validate_url(urljoin(current, location))
            continue

        if response.status_code >= 400:
            response.close()
            raise UrlFetchError(f"The page returned HTTP {response.status_code}.")

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(token in content_type for token in ("html", "text", "xml")):
            response.close()
            raise UrlFetchError(f"Unsupported content type '{content_type}'. Expected an HTML page.")

        chunks: List[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=8192):
            size += len(chunk)
            if size > MAX_BYTES:
                break
            chunks.append(chunk)
        response.close()

        raw = b"".join(chunks)
        try:
            html = raw.decode(response.encoding or "utf-8", errors="replace")
        except LookupError:
            html = raw.decode("utf-8", errors="replace")
        return current, html

    raise UrlFetchError("Too many redirects.")


def extract_readable_text(html: str) -> str:
    """Reduces an HTML document to the most posting-like readable text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(list(STRIP_TAGS)):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: text.__class__.__name__ == "Comment"):
        comment.extract()

    container = None
    for selector in CONTENT_SELECTORS:
        candidate = soup.select_one(selector)
        if candidate and len(candidate.get_text(" ", strip=True)) > 200:
            container = candidate
            break

    root = container or soup.body or soup
    lines = []
    for line in root.get_text("\n", strip=True).splitlines():
        cleaned = " ".join(line.split())
        if cleaned:
            lines.append(cleaned)

    # Collapse consecutive duplicates produced by nested layout containers.
    deduped: List[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    return "\n".join(deduped)[:MAX_TEXT_CHARS].strip()


def fetch_url_text(url: str) -> Dict[str, str]:
    """Fetches a job advertisement URL and returns its readable text plus a title."""
    final_url, html = _fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    page_title = (soup.title.get_text(strip=True) if soup.title else "") or ""
    text = extract_readable_text(html)

    if len(text) < 40:
        raise UrlFetchError(
            "The page loaded but contained almost no readable text. "
            "It may require a login or render entirely with JavaScript — paste the text instead."
        )

    return {
        "url": final_url,
        "requested_url": url,
        "page_title": page_title[:300],
        "text": text,
    }
