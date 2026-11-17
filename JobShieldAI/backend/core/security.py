"""
Security helpers.

This project has no user accounts, so there is no authentication to implement. What it
*does* need is protection from the two attacks a "fetch this URL for me" endpoint
inevitably invites:

1. **SSRF** — a client submitting `http://169.254.169.254/` to read cloud metadata, or
   `http://localhost:8000/api/history` to reach internal services.
2. **Response-size / slowloris abuse** — a URL that streams gigabytes or never finishes.

`validate_public_url` and `guarded_get` handle both.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

from backend.config import settings

USER_AGENT = "JobShieldAI/3.0 (+https://github.com/balachandu187/jobfraud)"


class UnsafeUrlError(ValueError):
    """Raised when a URL is disallowed by the fetch policy."""


def ca_bundle() -> Optional[str]:
    """
    Returns a CA bundle path to use for outbound TLS.

    Order: explicit override, then the OS trust store. Some slim container images ship a
    stale certifi bundle, so the OS path is preferred when it exists.
    """
    for candidate in (settings.ca_bundle, "/etc/ssl/certs/ca-certificates.crt",
                      "/etc/pki/tls/certs/ca-bundle.crt"):
        if candidate and os_path_isfile(candidate):
            return candidate
    return None


def os_path_isfile(path: str) -> bool:  # small indirection keeps imports tidy
    import os

    return os.path.isfile(path)


def _is_public_host(hostname: str) -> bool:
    """True only when every address the host resolves to is publicly routable."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host '{hostname}'.") from exc

    if not infos:
        raise UnsafeUrlError(f"Could not resolve host '{hostname}'.")

    for info in infos:
        raw = str(info[4][0]).split("%")[0]
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if (address.is_private or address.is_loopback or address.is_link_local
                or address.is_multicast or address.is_reserved or address.is_unspecified):
            return False
    return True


def validate_public_url(url: str) -> str:
    """Validates scheme + host and returns the normalised URL. Raises UnsafeUrlError."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http and https URLs can be analysed.")
    if not parsed.hostname:
        raise UnsafeUrlError("That URL has no host name.")
    if not _is_public_host(parsed.hostname):
        raise UnsafeUrlError(
            "Refusing to fetch a private, loopback or link-local address. "
            "Paste the advertisement text directly instead."
        )
    return parsed.geturl()


def guarded_get(url: str) -> Dict[str, Any]:
    """
    Fetches a URL under the fetch policy and returns {url, content_type, text}.

    Redirects are followed manually so every hop is re-validated — otherwise a public
    URL could redirect to 169.254.169.254 and bypass the initial check.
    """
    current = validate_public_url(url)
    verify = ca_bundle() or True
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})

    for _ in range(settings.url_max_redirects + 1):
        try:
            response = session.get(
                current,
                timeout=settings.url_fetch_timeout,
                stream=True,
                allow_redirects=False,
                headers={"Accept": "text/html,application/xhtml+xml"},
                verify=verify,
            )
        except requests.exceptions.SSLError as exc:
            raise UnsafeUrlError(
                "TLS certificate verification failed for that host. Behind a corporate "
                "proxy, set JOBSHIELD_CA_BUNDLE to your CA file."
            ) from exc
        except requests.exceptions.ConnectTimeout as exc:
            raise UnsafeUrlError("The host timed out while connecting.") from exc
        except requests.exceptions.ReadTimeout as exc:
            raise UnsafeUrlError("The host took too long to respond.") from exc
        except requests.exceptions.RequestException as exc:
            raise UnsafeUrlError(f"Could not reach that URL ({type(exc).__name__}).") from exc

        if response.is_redirect:
            location = response.headers.get("Location", "")
            response.close()
            if not location:
                raise UnsafeUrlError("Server redirected without a target location.")
            current = validate_public_url(urljoin(current, location))
            continue

        if response.status_code >= 400:
            response.close()
            raise UnsafeUrlError(f"The page returned HTTP {response.status_code}.")

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(
            token in content_type for token in ("html", "text", "xml")
        ):
            response.close()
            raise UnsafeUrlError(
                f"Unsupported content type '{content_type}'. Expected an HTML page."
            )

        chunks: List[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=8192):
            size += len(chunk)
            if size > settings.url_max_bytes:
                break
            chunks.append(chunk)
        response.close()

        raw = b"".join(chunks)
        encoding = response.encoding or "utf-8"
        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")

        return {"url": current, "content_type": content_type, "html": text}

    raise UnsafeUrlError("Too many redirects.")
