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
    family = OPERATIONS["extend"][DEFAULTS["extend"]]
    seconds = family.duration_range[0]
    result = json.loads(_handler("extend", client)(
        {"prompt": "the car drives off", "video_url": str(clip), "duration": seconds}))
    assert result["success"] is True
    assert result["video"] == "https://fal.media/out.mp4"
    assert result["model"] == DEFAULTS["extend"]
    assert result["endpoint"] == family.endpoint
    endpoint, payload = client.submissions[0]
    assert endpoint == family.endpoint
    assert payload["video_url"] == "https://fal.media/uploads/in.mp4"
    assert payload["prompt"] == "the car drives off" and payload["duration"] == seconds


def test_reference_uploads_local_images_and_videos(keyed, tmp_path) -> None:
    model, family = next((n, f) for n, f in OPERATIONS["reference"].items()
                         if f.max_references and f.max_video_references)
    photo = tmp_path / "face.png"
    photo.write_bytes(b"\0")
    motion = tmp_path / "dance.mov"
    motion.write_bytes(b"\0")
    client = FakeClient()
    result = json.loads(_handler("reference", client)({
        "prompt": "@Image1 dances like @Video1", "model": model,
        "reference_image_urls": [str(photo)], "reference_video_urls": [str(motion)]}))
    assert result["success"] is True, result
    payload = client.submissions[0][1]
    assert payload[family.reference_key] == ["https://fal.media/uploads/face.png"]
    assert payload[family.video_reference_key] == ["https://fal.media/uploads/dance.mov"]
    assert client.uploads == [photo.resolve(), motion.resolve()]


def test_a_reference_video_is_not_accepted_as_an_image(keyed, tmp_path) -> None:
    motion = tmp_path / "dance.mp4"
    motion.write_bytes(b"\0")
    client = FakeClient()
    result = json.loads(_handler("reference", client)(
        {"prompt": "p", "reference_image_urls": [str(motion)]}))
    assert result["error_type"] == "invalid_argument"
    assert client.uploads == [] and client.submissions == []


def test_invalid_arguments_fail_before_any_upload(keyed, tmp_path) -> None:
    clip = tmp_path / "in.mp4"
    clip.write_bytes(b"\0")
    client = FakeClient()
    result = json.loads(_handler("edit", client)(
        {"prompt": "p", "video_url": str(clip), "resolution": "8k"}))
    assert result["success"] is False and result["error_type"] == "invalid_argument"
    assert "resolution must be one of" in result["error"]
    assert client.uploads == [] and client.submissions == []


@pytest.mark.parametrize("operation", list(OPERATIONS))
def test_default_model_is_used_when_none_is_given(keyed, operation) -> None:
    client = FakeClient()
    args = {"prompt": "p", "reference_image_urls": ["https://a/1.png"]}
    if operation != "reference":
        args = {"prompt": "p", "video_url": "https://v/in.mp4"}
    result = json.loads(_handler(operation, client)(args))
    assert result["model"] == DEFAULTS[operation], result
    assert client.submissions[0][0] == OPERATIONS[operation][DEFAULTS[operation]].endpoint


def test_unknown_model_and_missing_key(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(tools, "get_fal_key", lambda: "fal-key")
    unknown = json.loads(_handler("extend", client)({"prompt": "p", "model": "veo0.1"}))
    assert DEFAULTS["extend"] in unknown["error"]
    monkeypatch.setattr(tools, "get_fal_key", lambda: "")
    missing = json.loads(_handler("extend", client)({"prompt": "p", "video_url": "https://v"}))
    assert missing["error_type"] == "auth_required"
    assert client.submissions == []


def test_reference_lists_must_be_lists(keyed) -> None:
    for name in ("reference_image_urls", "reference_video_urls"):
        result = json.loads(_handler("reference", FakeClient())({"prompt": "p", name: "x"}))
        assert result["error_type"] == "invalid_argument" and name in result["error"]


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
        for name, family in families.items():
            assert f"`{name}`" in props["model"]["description"]
            enum = props.get("resolution", {}).get("enum", [])
            assert {r.lower() for r in family.resolutions} <= set(enum)
            assert set(family.aspect_ratios) <= set(props.get("aspect_ratio", {}).get("enum", []))
            if family.duration_range:
                assert "duration" in props
            if family.max_references:
                assert "reference_image_urls" in props
            if family.max_video_references:
                assert "reference_video_urls" in props
            if family.audio_key:
                assert "audio" in props
        enum = props.get("resolution", {}).get("enum", [])
        assert len(enum) == len(set(enum)) and all(v == v.lower() for v in enum)
        assert all(isinstance(p.get("description"), str) for p in props.values())
