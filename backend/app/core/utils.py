"""Shared utility functions for the application."""

import ipaddress
import json
import logging
import os
import socket
import tempfile
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# Centralised Graph API version — bump this single constant to upgrade everywhere
GRAPH_API_VERSION = "v24.0"

IMAGE_CONTENT_TYPES = frozenset({"image/gif", "image/jpeg", "image/png", "image/webp"})
VIDEO_CONTENT_TYPES = frozenset({"video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"})
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 3
_KNOWN_MEDIA_DOMAINS = {"fal.media", "v3.fal.media", "cdn.fal.ai", "storage.googleapis.com"}


def allowed_media_domains() -> list[str]:
    """Return the explicit public media hosts permitted by configuration."""
    domains = set(_KNOWN_MEDIA_DOMAINS)
    configured = os.getenv("ALLOWED_MEDIA_DOMAINS", "")
    domains.update(domain.strip().lower().rstrip(".") for domain in configured.split(",") if domain.strip())
    r2_host = urlparse(os.getenv("R2_PUBLIC_URL", "")).hostname
    if r2_host:
        domains.add(r2_host.lower().rstrip("."))
    return sorted(domains)


def validate_url(url: str, allowed_domains: list[str] | None = None) -> bool:
    """Allow only public HTTPS URLs, resolving DNS before each outbound request."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443):
            return False
        hostname = (parsed.hostname or "").rstrip(".").lower()
        if not hostname:
            return False
        if allowed_domains:
            domains = {domain.rstrip(".").lower() for domain in allowed_domains}
            if not any(hostname == domain or hostname.endswith("." + domain) for domain in domains):
                return False

        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_global
        except ValueError:
            pass

        if hostname in {"localhost", "metadata.google.internal"}:
            return False
        addresses = {
            address[4][0]
            for address in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        }
        return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
    except (OSError, ValueError):
        return False


def _media_signature_is_valid(content: bytes, media_kind: str) -> bool:
    if media_kind == "image":
        return (
            content.startswith(b"\xff\xd8\xff")
            or content.startswith(b"\x89PNG\r\n\x1a\n")
            or content.startswith((b"GIF87a", b"GIF89a"))
            or (content.startswith(b"RIFF") and content[8:12] == b"WEBP")
        )
    if media_kind == "video":
        return (
            len(content) >= 12 and content[4:8] == b"ftyp"
        ) or content.startswith(b"\x1a\x45\xdf\xa3") or (
            content.startswith(b"RIFF") and content[8:12] == b"AVI "
        )
    return False


def validate_media_bytes(content: bytes, *, media_kind: str, max_bytes: int) -> None:
    """Reject oversized or mislabelled local media before forwarding it to a provider."""
    if len(content) > max_bytes:
        raise ValueError("Media exceeds the allowed size")
    if not _media_signature_is_valid(content[:16], media_kind):
        raise ValueError("Media does not match an allowed file signature")


def _validated_content_type(response: httpx.Response, allowed_mime_types: set[str] | frozenset[str]) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in allowed_mime_types:
        raise ValueError("Remote media response has an unsupported content type")
    return content_type


def _validate_content_length(response: httpx.Response, max_bytes: int) -> None:
    content_length = response.headers.get("content-length")
    if content_length and (not content_length.isdigit() or int(content_length) > max_bytes):
        raise ValueError("Remote media exceeds the allowed size")


def _remote_suffix(url: str, default_suffix: str, allowed_extensions: set[str] | None) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if allowed_extensions and suffix not in allowed_extensions:
        return default_suffix
    return suffix or default_suffix


def download_remote_media_to_tempfile(
    url: str,
    *,
    media_kind: str,
    allowed_mime_types: set[str] | frozenset[str],
    max_bytes: int,
    timeout: float,
    default_suffix: str,
    allowed_extensions: set[str] | None = None,
    allowed_domains: list[str] | None = None,
) -> str:
    """Download public media after validating each redirect and its contents."""
    current_url = url
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            if not validate_url(current_url, allowed_domains=allowed_domains):
                raise ValueError("Remote media URL is not an allowed public HTTPS URL")
            with client.stream("GET", current_url) as response:
                if response.status_code in _REDIRECT_STATUS_CODES:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Remote media redirect has no location")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                _validated_content_type(response, allowed_mime_types)
                _validate_content_length(response, max_bytes)
                temp_path = ""
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=_remote_suffix(current_url, default_suffix, allowed_extensions), delete=False
                    ) as temp_file:
                        temp_path = temp_file.name
                        head = b""
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise ValueError("Remote media exceeds the allowed size")
                            if len(head) < 16:
                                head += chunk[: 16 - len(head)]
                            temp_file.write(chunk)
                    if not _media_signature_is_valid(head, media_kind):
                        raise ValueError("Remote media does not match an allowed file signature")
                    return temp_path
                except Exception:
                    if temp_path:
                        Path(temp_path).unlink(missing_ok=True)
                    raise
    raise ValueError("Remote media exceeded the redirect limit")


async def download_remote_media(
    url: str,
    *,
    media_kind: str,
    allowed_mime_types: set[str] | frozenset[str],
    max_bytes: int,
    timeout: float = 30.0,
    allowed_domains: list[str] | None = None,
) -> tuple[bytes, str]:
    """Fetch public media bytes with the same redirect, size, MIME, and magic checks."""
    current_url = url
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            if not validate_url(current_url, allowed_domains=allowed_domains):
                raise ValueError("Remote media URL is not an allowed public HTTPS URL")
            async with client.stream("GET", current_url) as response:
                if response.status_code in _REDIRECT_STATUS_CODES:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Remote media redirect has no location")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                content_type = _validated_content_type(response, allowed_mime_types)
                _validate_content_length(response, max_bytes)
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise ValueError("Remote media exceeds the allowed size")
                if not _media_signature_is_valid(bytes(content[:16]), media_kind):
                    raise ValueError("Remote media does not match an allowed file signature")
                return bytes(content), content_type
    raise ValueError("Remote media exceeded the redirect limit")


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
