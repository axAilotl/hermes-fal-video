from __future__ import annotations

import pytest

from hermes_fal_video.families import OPERATIONS, Family
from hermes_fal_video.payloads import InvalidRequest, Request, build_payload

ALL = [(op, name, family) for op, families in OPERATIONS.items()
       for name, family in families.items()]
IDS = [f"{op}:{name}" for op, name, _ in ALL]


def _pick(predicate, operation: str | None = None) -> tuple[str, str, Family]:
    for op, name, family in ALL:
        if (operation is None or op == operation) and predicate(family):
            return op, name, family
    pytest.skip("no family has this shape")


def _base(operation: str, family: Family, **changes) -> Request:
    needs_image = operation == "reference" or family.references_required
    fields = {
        "prompt": "p",
        "video_url": "https://v/in.mp4" if operation in ("edit", "extend") else None,
        "reference_urls": ("https://a/1.png",) if needs_image else (),
    }
    fields.update(changes)
    return Request(**fields)


@pytest.mark.parametrize(("operation", "model", "family"), ALL, ids=IDS)
def test_every_family_builds_its_boundary_requests(operation, model, family) -> None:
    payload = build_payload(operation, model, family, _base(operation, family, prompt="  p  "))
    assert payload["prompt"] == "p"
    assert dict(family.fixed).items() <= payload.items()
    if family.duration_range:
        low, high = family.duration_range
        for seconds in (low, high):
            built = build_payload(operation, model, family, _base(operation, family,
                                                                   duration=seconds))
            assert built["duration"] == (str(seconds) if family.duration_as_string else seconds)
        for outside in (low - 1, high + 1):
            with pytest.raises(InvalidRequest, match=f"{low}-{high}"):
                build_payload(operation, model, family, _base(operation, family,
                                                              duration=outside))
    for value in family.resolutions:
        built = build_payload(operation, model, family,
                              _base(operation, family, resolution=value.lower()))
        assert built["resolution"] == value  # FAL's own spelling, whatever case was given
    for value in family.aspect_ratios:
        built = build_payload(operation, model, family, _base(operation, family,
                                                               aspect_ratio=value))
        assert built["aspect_ratio"] == value


@pytest.mark.parametrize(("operation", "model", "family"), ALL, ids=IDS)
def test_reference_limits_and_keys(operation, model, family) -> None:
    images = ("https://a/i.png",) * family.max_references
    videos = ("https://a/v.mp4",) * family.max_video_references
    payload = build_payload(operation, model, family, _base(
        operation, family, reference_urls=images or _base(operation, family).reference_urls,
        video_reference_urls=videos))
    if images:
        assert payload[family.reference_key] == list(images)
    if videos:
        assert payload[family.video_reference_key] == list(videos)
    with pytest.raises(InvalidRequest, match="image"):
        build_payload(operation, model, family, _base(
            operation, family, reference_urls=images + ("https://a/x.png",)))
    with pytest.raises(InvalidRequest, match="video"):
        build_payload(operation, model, family, _base(
            operation, family, video_reference_urls=videos + ("https://a/x.mp4",)))


@pytest.mark.parametrize(("operation", "model", "family"), ALL, ids=IDS)
def test_unsupported_options_are_refused_by_name(operation, model, family) -> None:
    unsupported = {
        "seed": (not family.seed, 1),
        "audio": (not family.audio_key, True),
        "keep_audio": (not family.keep_audio, True),
        "duration": (family.duration_range is None, 5),
        "resolution": (not family.resolutions, "720p"),
        "aspect_ratio": (not family.aspect_ratios, "16:9"),
    }
    for name, (refused, value) in unsupported.items():
        if refused:
            with pytest.raises(InvalidRequest, match=f"does not take {name}"):
                build_payload(operation, model, family, _base(operation, family,
                                                              **{name: value}))


def test_audio_switch_uses_the_family_key() -> None:
    for op, name, family in ALL:
        if family.audio_key:
            payload = build_payload(op, name, family, _base(op, family, audio=False))
            assert payload[family.audio_key] is False
            assert "generate_audio" not in payload or family.audio_key == "generate_audio"


def test_auto_and_adaptive_aspect_ratios_are_interchangeable() -> None:
    op, name, family = _pick(lambda f: "adaptive" in f.aspect_ratios)
    assert build_payload(op, name, family, _base(op, family, aspect_ratio="auto"))[
        "aspect_ratio"] == "adaptive"
    op, name, family = _pick(lambda f: "auto" in f.aspect_ratios)
    assert build_payload(op, name, family, _base(op, family, aspect_ratio="adaptive"))[
        "aspect_ratio"] == "auto"


def test_string_durations_and_auto() -> None:
    op, name, family = _pick(lambda f: f.duration_as_string and f.duration_auto)
    low = family.duration_range[0]
    assert build_payload(op, name, family, _base(op, family, duration=f"{low}s"))[
        "duration"] == str(low)
    assert build_payload(op, name, family, _base(op, family, duration="auto"))[
        "duration"] == "auto"
    op, name, family = _pick(lambda f: f.duration_range and not f.duration_auto)
    with pytest.raises(InvalidRequest):
        build_payload(op, name, family, _base(op, family, duration="auto"))


def test_keep_audio_maps_to_audio_setting() -> None:
    op, name, family = _pick(lambda f: f.keep_audio, "edit")
    assert build_payload(op, name, family, _base(op, family, keep_audio=True))[
        "audio_setting"] == "origin"
    assert build_payload(op, name, family, _base(op, family, keep_audio=False))[
        "audio_setting"] == "auto"


def test_reference_operation_accepts_videos_alone_unless_images_are_required() -> None:
    op, name, family = _pick(
        lambda f: f.max_video_references and not f.references_required, "reference")
    payload = build_payload(op, name, family, Request(
        prompt="p", video_reference_urls=("https://a/v.mp4",)))
    assert payload[family.video_reference_key] == ["https://a/v.mp4"]
    with pytest.raises(InvalidRequest, match="at least one reference"):
        build_payload(op, name, family, Request(prompt="p"))
    op, name, family = _pick(lambda f: f.references_required)
    with pytest.raises(InvalidRequest, match="at least one reference image"):
        build_payload(op, name, family, Request(prompt="p"))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"video_url": None}, "video_url is required"),
        ({"prompt": " "}, "prompt is required"),
        ({"resolution": "1440x900"}, "resolution must be one of"),
        ({"resolution": 720}, "resolution must be one of"),
        ({"seed": -1}, "seed must be an integer"),
        ({"seed": True}, "seed must be an integer"),
        ({"seed": 2**31}, "seed must be an integer"),
        ({"duration": True}, "seconds"),
        ({"duration": "soon"}, "seconds"),
    ],
)
def test_invalid_requests_name_the_problem(changes, message) -> None:
    op, name, family = _pick(lambda f: f.seed and f.resolutions and f.duration_range, "extend")
    with pytest.raises(InvalidRequest, match=message):
        build_payload(op, name, family, _base(op, family, **changes))


def test_family_table_is_internally_consistent() -> None:
    suffix = {"edit": ("edit", "edit-video", "video-edit", "video-to-video"),
              "extend": ("extend", "extend-video", "extend-video/draft"),
              "reference": ("reference-to-video",)}
    for operation, name, family in ALL:
        assert family.endpoint.endswith(suffix[operation]), family.endpoint
        assert bool(family.reference_key) == bool(family.max_references), name
        assert bool(family.video_reference_key) == bool(family.max_video_references), name
        assert not family.references_required or family.max_references, name
        if family.duration_range:
            assert 0 < family.duration_range[0] <= family.duration_range[1], name
        lowered = [r.lower() for r in family.resolutions]
        assert len(set(lowered)) == len(lowered), name
        assert family.notes and family.display, name
    for operation, families in OPERATIONS.items():
        endpoints = [f.endpoint for f in families.values()]
        assert len(set(endpoints)) == len(endpoints), operation
