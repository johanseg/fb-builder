"""Shared utility functions for the application."""

import ipaddress
import json
import logging
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Centralised Graph API version — bump this single constant to upgrade everywhere
GRAPH_API_VERSION = "v21.0"


def validate_url(url: str, allowed_domains: list[str] | None = None) -> bool:
    """Validate URL is safe - not pointing to internal networks (SSRF prevention)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block private/internal IPs
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass  # It's a hostname, not an IP — that's fine
        # Block common internal hostnames
        if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254', 'metadata.google.internal'):  # nosec B104
            return False
        # Check allowed domains if specified
        if allowed_domains:
            if not any(hostname == d or hostname.endswith('.' + d) for d in allowed_domains):
                return False
        return True
    except Exception:
        return False


def extract_json_from_text(text: str):
    """Extract JSON from plain text or markdown fenced code blocks."""
    stripped = text.strip()

    if "```json" in stripped:
        start = stripped.find("```json") + len("```json")
        end = stripped.find("```", start)
        stripped = stripped[start:end if end != -1 else None].strip()
    elif stripped.startswith("```"):
        start = len("```")
        end = stripped.find("```", start)
        stripped = stripped[start:end if end != -1 else None].strip()

    return json.loads(stripped)


def extract_markdown_list_items(text: str) -> list[str]:
    """Extract bullet or numbered list items from multiline markdown text."""
    pattern = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$")
    items = []

    for raw_line in text.splitlines():
        match = pattern.match(raw_line)
        if match:
            items.append(match.group(1).strip())

    stripped = text.strip()
    if items:
        return items
    if stripped:
        return [stripped]
    return []


def resolve_managed_upload_path(reference: str | None, upload_dir: Path) -> Path | None:
    """Resolve a managed `/uploads/...` reference to a local file inside upload_dir."""
    if not reference:
        return None

    parsed = urlparse(reference)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = PurePosixPath(parsed.path or reference)
    parts = candidate.parts[1:] if candidate.is_absolute() else candidate.parts

    if len(parts) != 2 or parts[0] != "uploads":
        return None

    if any(part in {".", ".."} for part in parts):
        return None

    resolved_upload_dir = upload_dir.resolve()
    resolved_path = (resolved_upload_dir / parts[1]).resolve()

    if not resolved_path.is_relative_to(resolved_upload_dir):
        return None
    if not resolved_path.is_file():
        return None

    return resolved_path
