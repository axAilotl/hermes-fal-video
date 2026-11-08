"""Pure request building: validate tool arguments against a family and shape the FAL payload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .families import Family


class InvalidRequest(ValueError):
    """An argument the chosen FAL family cannot accept; the message names the allowed values."""


@dataclass(frozen=True)
class Request:
    prompt: str
    video_url: str | None = None
    reference_urls: tuple[str, ...] = ()
    resolution: str | None = None
    aspect_ratio: str | None = None
    duration: Any = None
    seed: Any = None
    audio: Any = None
    keep_audio: Any = None


def _choice(name: str, value: str | None, allowed: tuple[str, ...], model: str) -> str | None:
    if value is None:
        return None
    if not allowed:
        raise InvalidRequest(f"{model} does not take {name}.")
    if value not in allowed:
        raise InvalidRequest(f"{model} {name} must be one of: {', '.join(allowed)}.")
    return value


def _duration(family: Family, value: Any, model: str) -> Any:
    if value is None:
        return None
    if family.duration_range is None:
        raise InvalidRequest(f"{model} does not take duration.")
    if family.duration_auto and isinstance(value, str) and value.strip().lower() == "auto":
        return "auto"
    low, high = family.duration_range
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise InvalidRequest(f"{model} duration must be {low}-{high} seconds.")
    try:
        seconds = int(float(str(value).strip().removesuffix("s")))
    except ValueError:
        raise InvalidRequest(f"{model} duration must be {low}-{high} seconds.") from None
    if not low <= seconds <= high:
        raise InvalidRequest(f"{model} duration must be {low}-{high} seconds.")
    return str(seconds) if family.duration_as_string else seconds


def _flag(name: str, value: Any, supported: bool, model: str) -> bool | None:
    if value is None:
        return None
    if not supported:
        raise InvalidRequest(f"{model} does not take {name}.")
    if not isinstance(value, bool):
        raise InvalidRequest(f"{name} must be true or false.")
    return value


def build_payload(operation: str, model: str, family: Family, request: Request) -> dict[str, Any]:
    prompt = request.prompt.strip() if isinstance(request.prompt, str) else ""
    if not prompt:
        raise InvalidRequest("prompt is required.")
    payload: dict[str, Any] = {"prompt": prompt}

    if operation in ("edit", "extend"):
        if not request.video_url:
            raise InvalidRequest("video_url is required.")
        payload["video_url"] = request.video_url

    refs = list(request.reference_urls)
    if operation == "reference" and not refs:
        raise InvalidRequest("reference_image_urls needs at least one image.")
    if refs:
        if not family.reference_key:
            raise InvalidRequest(f"{model} does not take reference images.")
        if len(refs) > family.max_references:
            raise InvalidRequest(f"{model} takes at most {family.max_references} reference images.")
        payload[family.reference_key] = refs

    resolution = _choice("resolution", request.resolution, family.resolutions, model)
    if resolution is not None:
        payload["resolution"] = resolution
    aspect_ratio = _choice("aspect_ratio", request.aspect_ratio, family.aspect_ratios, model)
    if aspect_ratio is not None:
        payload["aspect_ratio"] = aspect_ratio
    duration = _duration(family, request.duration, model)
    if duration is not None:
        payload["duration"] = duration

    if request.seed is not None:
        if not family.seed:
            raise InvalidRequest(f"{model} does not take seed.")
        if isinstance(request.seed, bool) or not isinstance(request.seed, int):
            raise InvalidRequest("seed must be an integer.")
        payload["seed"] = request.seed
    audio = _flag("audio", request.audio, family.audio_toggle, model)
    if audio is not None:
        payload["generate_audio"] = audio
    keep_audio = _flag("keep_audio", request.keep_audio, family.keep_audio, model)
    if keep_audio is not None:
        payload["audio_setting"] = "origin" if keep_audio else "auto"
    return payload
