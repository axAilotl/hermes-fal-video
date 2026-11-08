from __future__ import annotations

import json

import pytest
from conftest import FakeClient

from hermes_fal_video import tools
from hermes_fal_video.families import DEFAULTS, OPERATIONS


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setattr(tools, "get_fal_key", lambda: "fal-key")


def _handler(operation: str, client: FakeClient, settings: dict | None = None):
    settings = settings or {}
    return tools.make_handler(operation, lambda key, default=None: settings.get(key, default),
                              make_client=lambda _key: client)


def test_extend_uploads_local_clip_and_returns_video(keyed, tmp_path) -> None:
    clip = tmp_path / "in.mp4"
    clip.write_bytes(b"\0" * 8)
    client = FakeClient()
    result = json.loads(_handler("extend", client)(
        {"prompt": "the car drives off", "video_url": str(clip), "duration": 4}))
    assert result["success"] is True
    assert result["video"] == "https://fal.media/out.mp4"
    assert result["endpoint"] == "xai/grok-imagine-video/extend-video"
    assert client.submissions == [("xai/grok-imagine-video/extend-video", {
        "prompt": "the car drives off", "video_url": "https://fal.media/uploads/in.mp4",
        "duration": 4})]


def test_invalid_arguments_fail_before_any_upload(keyed, tmp_path) -> None:
    clip = tmp_path / "in.mp4"
    clip.write_bytes(b"\0")
    client = FakeClient()
    result = json.loads(_handler("edit", client)(
        {"prompt": "p", "video_url": str(clip), "resolution": "4k"}))
    assert result["success"] is False and result["error_type"] == "invalid_argument"
    assert "auto, 480p, 720p" in result["error"]
    assert client.uploads == [] and client.submissions == []


def test_reference_defaults_to_seedance(keyed) -> None:
    client = FakeClient()
    result = json.loads(_handler("reference", client)(
        {"prompt": "p", "reference_image_urls": ["https://a/1.png"]}))
    assert result["model"] == "seedance-2.0"
    assert client.submissions[0][0] == "bytedance/seedance-2.0/reference-to-video"


def test_unknown_model_and_missing_key(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(tools, "get_fal_key", lambda: "fal-key")
    unknown = json.loads(_handler("extend", client)({"prompt": "p", "model": "veo3.1"}))
    assert "grok-imagine" in unknown["error"]
    monkeypatch.setattr(tools, "get_fal_key", lambda: "")
    missing = json.loads(_handler("extend", client)({"prompt": "p", "video_url": "https://v"}))
    assert missing["error_type"] == "auth_required"
    assert client.submissions == []


def test_api_failure_and_empty_result_are_errors(keyed) -> None:
    class Failing(FakeClient):
        def submit(self, endpoint, arguments):
            raise RuntimeError("422: unsupported video codec")

    failed = json.loads(_handler("extend", Failing())({"prompt": "p", "video_url": "https://v"}))
    assert failed["error_type"] == "api_error" and "unsupported video codec" in failed["error"]
    empty = json.loads(_handler("extend", FakeClient(result={}))(
        {"prompt": "p", "video_url": "https://v"}))
    assert empty["error_type"] == "empty_response"


def test_schemas_cover_every_family_value() -> None:
    for operation, families in OPERATIONS.items():
        schema = tools._schema(operation)
        props = schema["parameters"]["properties"]
        assert schema["name"] == tools.TOOL_NAMES[operation]
        assert props["model"]["enum"] == list(families)
        assert DEFAULTS[operation] in families
        for family in families.values():
            assert set(family.resolutions) <= set(props.get("resolution", {}).get("enum", []))
            assert set(family.aspect_ratios) <= set(props.get("aspect_ratio", {}).get("enum", []))
            if family.duration_range:
                assert "duration" in props
            if family.max_references:
                assert "reference_image_urls" in props
        assert all(isinstance(p.get("description"), str) for p in props.values())
