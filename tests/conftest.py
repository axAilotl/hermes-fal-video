from __future__ import annotations

from pathlib import Path

import fal_client
import pytest


class FakeHandle:
    def __init__(self, statuses: list, result: dict, request_id: str = "req-123") -> None:
        self._statuses = list(statuses)
        self._result = result
        self.request_id = request_id
        self.cancelled = False

    def status(self, **_kwargs):
        return self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]

    def get(self):
        return self._result

    def cancel(self):
        self.cancelled = True


class FakeClient:
    """Records uploads and submissions instead of talking to FAL."""

    def __init__(self, statuses: list | None = None, result: dict | None = None) -> None:
        self.uploads: list[Path] = []
        self.submissions: list[tuple[str, dict]] = []
        self.handle = FakeHandle(
            statuses or [fal_client.Completed(logs=None, metrics={})],
            result if result is not None else {"video": {"url": "https://fal.media/out.mp4",
                                                         "content_type": "video/mp4"}},
        )

    def upload_file(self, path):
        self.uploads.append(Path(path))
        return f"https://fal.media/uploads/{Path(path).name}"

    def submit(self, endpoint, arguments):
        self.submissions.append((endpoint, arguments))
        return self.handle


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()
