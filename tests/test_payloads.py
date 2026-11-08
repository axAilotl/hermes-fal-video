from __future__ import annotations

import pytest

from hermes_fal_video.families import EDIT, OPERATIONS, REFERENCE
from hermes_fal_video.payloads import InvalidRequest, Request, build_payload


def test_seedance_reference_payload_uses_its_own_keys_and_string_duration() -> None:
    payload = build_payload("reference", "seedance-2.0", REFERENCE["seedance-2.0"], Request(
        prompt=" two friends wave ", reference_urls=("https://a/1.png", "https://a/2.png"),
        resolution="720p", aspect_ratio="9:16", duration=6, audio=False,
    ))
    assert payload == {
        "prompt": "two friends wave", "image_urls": ["https://a/1.png", "https://a/2.png"],
        "resolution": "720p", "aspect_ratio": "9:16", "duration": "6", "generate_audio": False,
    }


def test_grok_reference_uses_reference_image_urls_and_int_duration() -> None:
    payload = build_payload("reference", "grok-imagine", REFERENCE["grok-imagine"], Request(
        prompt="p", reference_urls=("https://a/1.png",), duration="5s"))
    assert payload["reference_image_urls"] == ["https://a/1.png"]
    assert payload["duration"] == 5


def test_seedance_accepts_auto_duration() -> None:
    payload = build_payload("reference", "seedance-2.0", REFERENCE["seedance-2.0"], Request(
        prompt="p", reference_urls=("https://a/1.png",), duration="auto"))
    assert payload["duration"] == "auto"


def test_happy_horse_edit_keeps_audio_and_takes_references() -> None:
    payload = build_payload("edit", "happy-horse", EDIT["happy-horse"], Request(
        prompt="p", video_url="https://v/in.mp4", reference_urls=("https://a/1.png",),
        keep_audio=True, seed=7))
    assert payload == {"prompt": "p", "video_url": "https://v/in.mp4",
                       "reference_image_urls": ["https://a/1.png"], "seed": 7,
                       "audio_setting": "origin"}


@pytest.mark.parametrize(
    ("operation", "model", "request_", "message"),
    [
        ("edit", "grok-imagine", Request(prompt="p"), "video_url is required"),
        ("edit", "grok-imagine", Request(prompt=" ", video_url="u"), "prompt is required"),
        ("edit", "grok-imagine", Request(prompt="p", video_url="u", resolution="1080p"),
         "auto, 480p, 720p"),
        ("edit", "grok-imagine", Request(prompt="p", video_url="u", reference_urls=("r",)),
         "does not take reference images"),
        ("edit", "grok-imagine", Request(prompt="p", video_url="u", keep_audio=True),
         "does not take keep_audio"),
        ("extend", "grok-imagine", Request(prompt="p", video_url="u", duration=11), "2-10"),
        ("extend", "grok-imagine", Request(prompt="p", video_url="u", duration=True), "2-10"),
        ("reference", "seedance-2.0", Request(prompt="p"), "at least one image"),
        ("reference", "grok-imagine", Request(prompt="p", reference_urls=("r",) * 8),
         "at most 7"),
        ("reference", "happy-horse", Request(prompt="p", reference_urls=("r",), audio=True),
         "does not take audio"),
        ("reference", "seedance-2.0", Request(prompt="p", reference_urls=("r",), seed=1),
         "does not take seed"),
    ],
)
def test_invalid_requests_name_the_problem(operation, model, request_, message) -> None:
    family = OPERATIONS[operation][model]
    with pytest.raises(InvalidRequest, match=message):
        build_payload(operation, model, family, request_)


def test_every_family_targets_its_operation_endpoint() -> None:
    suffix = {"edit": ("edit-video", "video-edit"), "extend": ("extend-video",),
              "reference": ("reference-to-video",)}
    for operation, families in OPERATIONS.items():
        for family in families.values():
            assert family.endpoint.endswith(suffix[operation]), family.endpoint
            assert bool(family.reference_key) == bool(family.max_references)
