"""Submit a FAL queue request and wait for it with a deadline, cancelling on timeout."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

POLL_SECONDS = 3.0


class FalTimeout(TimeoutError):
    def __init__(self, request_id: str, seconds: float) -> None:
        super().__init__(f"FAL request {request_id} did not finish within {int(seconds)} s")
        self.request_id = request_id


def run(
    client: Any,
    endpoint: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    from fal_client import Completed

    handle = client.submit(endpoint, arguments=payload)
    deadline = clock() + timeout_seconds
    while not isinstance(handle.status(), Completed):
        if clock() >= deadline:
            try:
                handle.cancel()
            except Exception as exc:  # the timeout is the error worth reporting
                logger.debug("Cancelling FAL request %s failed: %s", handle.request_id, exc)
            raise FalTimeout(handle.request_id, timeout_seconds)
        sleep(POLL_SECONDS)
    result = handle.get()
    return result if isinstance(result, dict) else {}


def video_url(result: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """Pull the output URL and useful metadata out of a FAL video result."""
    video = result.get("video")
    extra: dict[str, Any] = {}
    if isinstance(video, dict):
        for key in ("content_type", "file_size", "duration", "width", "height"):
            if video.get(key) is not None:
                extra[key] = video[key]
        url = video.get("url")
    else:
        url = video
    if result.get("seed") is not None:
        extra["seed"] = result["seed"]
    return (url if isinstance(url, str) and url else None), extra
