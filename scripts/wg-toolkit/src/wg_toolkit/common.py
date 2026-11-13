"""Validation, output, and error-reporting helpers shared by WG scripts."""

from __future__ import annotations

from datetime import date as calendar_date
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse


JsonObject = dict[str, Any]


def validate_date(value: str) -> str:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        calendar_date.fromisoformat(value)
    except ValueError:
        raise ValueError("Provide a valid date in YYYY-MM-DD format.") from None
    return value


def require_secure_url(url: str, label: str, allow_localhost: bool = True) -> None:
    parsed = urlparse(url)
    local = allow_localhost and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or parsed.username or parsed.password or not (
            parsed.scheme == "https" or (parsed.scheme == "http" and local)):
        raise ValueError(f"{label} requires HTTPS except for localhost.")


def is_zoom_host(hostname: str | None) -> bool:
    return hostname == "zoom.us" or (hostname or "").endswith(".zoom.us")


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def write_private_json(path: Path, value: Any) -> None:
    """Write JSON to a new owner-only file; never overwrite an existing one."""
    text = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(text)


def error_message(error: Exception) -> str:
    """Describe an error for the CLI without exposing URLs or credentials."""
    if isinstance(error, ExceptionGroup):
        messages = list(dict.fromkeys(error_message(child) for child in error.exceptions))
        return "; ".join(messages)
    if isinstance(error, (ValueError, OSError)):
        return re.sub(r"https?://\S+", "<redacted URL>", str(error))
    return f"MCP operation failed ({type(error).__name__}); check connection and access permissions."
