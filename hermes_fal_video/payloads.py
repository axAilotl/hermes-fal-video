"""Pure request building: validate tool arguments against a family and shape the FAL payload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .families import Family

_MAX_SEED = 2**31 - 1
# Two spellings of "let the model pick"; families accept one or the other.
_ALIASES = {"auto": "adaptive", "adaptive": "auto"}


class InvalidRequest(ValueError):
    """An argument the chosen FAL family cannot accept; the message names the allowed values."""


@dataclass(frozen=True)
class Request:
    prompt: str
    video_url: str | None = None
    reference_urls: tuple[str, ...] = ()
    video_reference_urls: tuple[str, ...] = ()
    resolution: str | None = None
    aspect_ratio: str | None = None
    duration: Any = None
    seed: Any = None
    audio: Any = None
    keep_audio: Any = None


def _choice(name: str, value: Any, allowed: tuple[str, ...], model: str) -> str | None:
    if value is None:
        return None
    if not allowed:
        raise InvalidRequest(f"{model} does not take {name}.")
    if isinstance(value, str):
        by_lower = {option.lower(): option for option in allowed}
        wanted = value.strip().lower()
        if wanted in by_lower:
            return by_lower[wanted]
        if _ALIASES.get(wanted) in by_lower:
            return by_lower[_ALIASES[wanted]]
    raise InvalidRequest(f"{model} {name} must be one of: {', '.join(allowed)}.")


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


def _references(urls: tuple[str, ...], key: str, limit: int, kind: str, model: str) -> list[str]:
    if not urls:
        return []
    if not key:
        raise InvalidRequest(f"{model} does not take reference {kind}s.")
    if len(urls) > limit:
        raise InvalidRequest(f"{model} takes at most {limit} reference {kind}s.")
    return list(urls)


def build_payload(operation: str, model: str, family: Family, request: Request) -> dict[str, Any]:
    prompt = request.prompt.strip() if isinstance(request.prompt, str) else ""
    if not prompt:
        raise InvalidRequest("prompt is required.")
    payload: dict[str, Any] = {"prompt": prompt, **dict(family.fixed)}

    if operation in ("edit", "extend"):
        if not request.video_url:
            raise InvalidRequest("video_url is required.")
        payload["video_url"] = request.video_url

    images = _references(request.reference_urls, family.reference_key, family.max_references,
                         "image", model)
    videos = _references(request.video_reference_urls, family.video_reference_key,
                         family.max_video_references, "video", model)
    if operation == "reference" and not images and not videos:
        raise InvalidRequest("Give at least one reference image or reference video.")
    if family.references_required and not images:
        raise InvalidRequest(f"{model} needs at least one reference image.")
    if images:
        payload[family.reference_key] = images
    if videos:
        payload[family.video_reference_key] = videos

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
        if isinstance(request.seed, bool) or not isinstance(request.seed, int) \
                or not 0 <= request.seed <= _MAX_SEED:
            raise InvalidRequest(f"seed must be an integer from 0 to {_MAX_SEED}.")
        payload["seed"] = request.seed
    audio = _flag("audio", request.audio, bool(family.audio_key), model)
    if audio is not None:
        payload[family.audio_key] = audio
    keep_audio = _flag("keep_audio", request.keep_audio, family.keep_audio, model)
    if keep_audio is not None:
        payload["audio_setting"] = "origin" if keep_audio else "auto"
    return payload
