from __future__ import annotations

import fal_client
import pytest
from conftest import FakeClient

from hermes_fal_video import runner


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_polls_until_completed_then_returns_result() -> None:
    client = FakeClient(statuses=[fal_client.Queued(position=2),
                                  fal_client.InProgress(logs=None),
                                  fal_client.Completed(logs=None, metrics={})])
    clock = Clock()
    result = runner.run(client, "xai/x", {"prompt": "p"}, 600, sleep=clock.sleep, clock=clock)
    assert result["video"]["url"] == "https://fal.media/out.mp4"
    assert client.submissions == [("xai/x", {"prompt": "p"})]
    assert clock.sleeps == [runner.POLL_SECONDS, runner.POLL_SECONDS]


def test_timeout_cancels_the_job_and_reports_its_id() -> None:
    client = FakeClient(statuses=[fal_client.InProgress(logs=None)])
    clock = Clock()
    with pytest.raises(runner.FalTimeout, match="req-123"):
        runner.run(client, "xai/x", {"prompt": "p"}, 60, sleep=clock.sleep, clock=clock)
    assert client.handle.cancelled is True


@pytest.mark.parametrize(
    ("result", "url", "extra"),
    [
        ({"video": {"url": "https://v", "file_size": 9}, "seed": 4}, "https://v",
         {"file_size": 9, "seed": 4}),
        ({"video": "https://v"}, "https://v", {}),
        ({"video": {}}, None, {}),
        ({}, None, {}),
    ],
)
def test_video_url_extraction(result, url, extra) -> None:
    assert runner.video_url(result) == (url, extra)
