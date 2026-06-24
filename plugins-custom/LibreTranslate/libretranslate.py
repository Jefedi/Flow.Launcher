# -*- coding: utf-8 -*-
"""LibreTranslate client logic, kept separate from the Flow Launcher plumbing.

This module has a single responsibility: take some text plus the user's
settings and return a translation (or raise a readable error). It deliberately
knows nothing about Flow Launcher's JSON-RPC protocol.
"""

import json
import urllib.error
import urllib.request

# Hard timeout so a slow/unreachable instance never freezes the Flow result list.
HTTP_TIMEOUT = 5


class TranslationError(Exception):
    """Raised with a human-readable message when a translation cannot be made."""


def _normalize_instance_url(instance_url):
    """Strip whitespace and any trailing slash from the configured base URL."""
    return (instance_url or "").strip().rstrip("/")


def translate(text, instance_url, target_lang, api_key=None, timeout=HTTP_TIMEOUT):
    """Translate ``text`` into ``target_lang`` via a LibreTranslate instance.

    Returns a ``(translated_text, detected_language)`` tuple. ``detected_language``
    may be an empty string if the server does not report one. Raises
    ``TranslationError`` with a readable message on any network/HTTP/parse failure.
    """
    base = _normalize_instance_url(instance_url)
    if not base:
        raise TranslationError("No instance URL configured (see plugin settings).")

    payload = {
        "q": text,
        "source": "auto",
        "target": target_lang or "en",
        "format": "text",
    }
    # Only send the API key when the user actually provided one.
    if api_key and api_key.strip():
        payload["api_key"] = api_key.strip()

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=base + "/translate",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Non-2xx: try to surface the server's error message if it sent one.
        message = _extract_error_message(exc) or f"HTTP {exc.code}"
        raise TranslationError(message)
    except urllib.error.URLError as exc:
        raise TranslationError(f"Network error: {exc.reason}")
    except TimeoutError:
        raise TranslationError(f"Timed out after {timeout}s")
    except Exception as exc:  # pragma: no cover - defensive catch-all
        raise TranslationError(str(exc))

    try:
        body = json.loads(raw)
    except ValueError:
        raise TranslationError("Invalid response from server (not JSON).")

    translated = body.get("translatedText")
    if not translated:
        # LibreTranslate also returns {"error": "..."} on logical failures.
        raise TranslationError(body.get("error") or "Empty translation returned.")

    detected = ""
    detected_block = body.get("detectedLanguage") or {}
    if isinstance(detected_block, dict):
        detected = detected_block.get("language", "") or ""

    return translated, detected


def _extract_error_message(http_error):
    """Best-effort extraction of LibreTranslate's JSON ``error`` field on failure."""
    try:
        raw = http_error.read().decode("utf-8", errors="replace")
        return json.loads(raw).get("error")
    except Exception:
        return None
