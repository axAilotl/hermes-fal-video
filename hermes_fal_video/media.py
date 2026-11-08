"""Turn tool media arguments into URLs FAL can fetch; only local media files are uploaded."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".webm", ".m4v", ".mkv"})
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


class MediaError(ValueError):
    """A media argument that cannot be sent to FAL; the message is safe to show the model."""


def _local_path(source: str) -> Path | None:
    parsed = urlparse(source)
    scheme = parsed.scheme.lower()
    if scheme in ("http", "https"):
        if not parsed.netloc:
            raise MediaError(f"Not a valid URL: {source}")
        return None
    if scheme == "file":
        return Path(unquote(parsed.path))
    if scheme and len(scheme) > 1:  # a one-letter "scheme" is a Windows drive letter
        raise MediaError(
            f"Unsupported media source scheme '{scheme}:' (use https or a local path)."
        )
    return Path(source)


def prepare(source: Any, kind: str, client: Any, max_bytes: int) -> str:
    """Return ``source`` if it is an http(s) URL, else upload the local media file it names.

    Only regular files with a media suffix (checked after resolving symlinks) and within
    ``max_bytes`` are uploaded, so the tools cannot be used to ship arbitrary local files.
    """
    if not isinstance(source, str) or not source.strip():
        raise MediaError(f"Expected a {kind} URL or local file path.")
    source = source.strip()
    path = _local_path(source)
    if path is None:
        return source
    allowed = VIDEO_SUFFIXES if kind == "video" else IMAGE_SUFFIXES
    try:
        resolved = path.expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise MediaError(f"Local {kind} file not found: {source}") from None
    if not resolved.is_file():
        raise MediaError(f"Not a regular file: {source}")
    if resolved.suffix.lower() not in allowed:
        raise MediaError(
            f"Local {kind} files must end in {', '.join(sorted(allowed))}: {source}"
        )
    size = resolved.stat().st_size
    if size == 0:
        raise MediaError(f"Local {kind} file is empty: {source}")
    if size > max_bytes:
        raise MediaError(f"Local {kind} file is over {max_bytes // (1024 * 1024)} MB: {source}")
    return client.upload_file(resolved)
