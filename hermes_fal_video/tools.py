"""The fal_video_* tools: schemas generated from the family table, and their handlers."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from . import media, runner
from .families import DEFAULTS, OPERATIONS, Family
from .payloads import InvalidRequest, Request, build_payload

logger = logging.getLogger(__name__)

TOOLSET = "fal_video"
FAL_KEY_ENV = "FAL_KEY"
_MAX_ERROR_CHARS = 500
TOOL_NAMES = {"edit": "fal_video_edit", "extend": "fal_video_extend",
              "reference": "fal_video_from_references"}

ConfigGetter = Callable[..., Any]


def get_fal_key() -> str:
    """Fail-closed profile-scoped read of FAL_KEY."""
    from agent.secret_scope import UnscopedSecretError, get_secret

    try:
        value = get_secret(FAL_KEY_ENV, None)
    except UnscopedSecretError:
        # Ambient credentials may belong to a different multiplexed profile.
        return ""
    return (value or "").strip()


def is_available() -> bool:
    try:
        import fal_client  # noqa: F401
    except ImportError:
        return False
    return bool(get_fal_key())


def _make_client(key: str) -> Any:
    import fal_client

    return fal_client.SyncClient(key=key)


def _int_setting(get_config: ConfigGetter, name: str, default: int, low: int, high: int) -> int:
    value = get_config(name, default)
    if isinstance(value, bool):
        return default
    try:
        return min(max(int(value), low), high)
    except (TypeError, ValueError):
        return default


def _models_description(families: dict[str, Family]) -> str:
    return " ".join(f"`{name}`: {family.notes}" for name, family in families.items())


def _union(families: dict[str, Family], attribute: str) -> list[str]:
    """Every value any family accepts, lowercased; payloads restore each family's spelling."""
    values: list[str] = []
    for family in families.values():
        values += [v.lower() for v in getattr(family, attribute) if v.lower() not in values]
    return values


def _schema(operation: str) -> dict[str, Any]:
    families = OPERATIONS[operation]
    properties: dict[str, Any] = {
        "prompt": {"type": "string", "description": "What the output video should show."},
        "model": {
            "type": "string",
            "enum": list(families),
            "description": f"FAL model family (default `{DEFAULTS[operation]}`). "
            + _models_description(families),
        },
    }
    required = ["prompt"]
    if operation in ("edit", "extend"):
        properties["video_url"] = {
            "type": "string",
            "description": "HTTPS URL or local path of the source video "
                           "(mp4, mov, webm, m4v, mkv).",
        }
        required.append("video_url")
    if any(f.max_references for f in families.values()):
        properties["reference_image_urls"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "HTTPS URLs or local paths of reference images (png, jpg, webp, gif).",
        }
    if any(f.max_video_references for f in families.values()):
        properties["reference_video_urls"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "HTTPS URLs or local paths of reference videos for motion, style "
                           "or subjects (mp4, mov, webm, m4v, mkv); not every model takes them.",
        }
    if resolutions := _union(families, "resolutions"):
        properties["resolution"] = {"type": "string", "enum": resolutions,
                                    "description": "Output resolution; varies by model."}
    if aspect_ratios := _union(families, "aspect_ratios"):
        properties["aspect_ratio"] = {"type": "string", "enum": aspect_ratios,
                                      "description": "Output aspect ratio; varies by model."}
    if any(f.duration_range for f in families.values()):
        ranges = ", ".join(f"{name} {f.duration_range[0]}-{f.duration_range[1]}"
                           for name, f in families.items() if f.duration_range)
        properties["duration"] = {
            "type": "integer",
            "description": f"Seconds of video to {'add' if operation == 'extend' else 'make'} "
            f"({ranges}).",
        }
    if any(f.seed for f in families.values()):
        properties["seed"] = {"type": "integer", "description": "Seed for repeatable output."}
    if any(f.audio_key for f in families.values()):
        properties["audio"] = {"type": "boolean", "description": "Generate a soundtrack."}
    if any(f.keep_audio for f in families.values()):
        properties["keep_audio"] = {"type": "boolean",
                                    "description": "Keep the source video's audio track."}
    verbs = {
        "edit": "Edit an existing video with a prompt using FAL.",
        "extend": "Continue an existing video past its last frame using FAL.",
        "reference": "Make a video that features the subjects in reference images or videos "
                     "using FAL.",
    }
    return {
        "name": TOOL_NAMES[operation],
        "description": verbs[operation] + " Returns the output video URL. Takes 1-10 minutes.",
        "parameters": {"type": "object", "properties": properties, "required": required},
    }



def _error(message: str, error_type: str, model: str = "") -> str:
    return json.dumps({"success": False, "video": None, "error": message[:_MAX_ERROR_CHARS],
                       "error_type": error_type, "model": model, "provider": "fal"})


def make_handler(operation: str, get_config: ConfigGetter, make_client=_make_client):
    families = OPERATIONS[operation]

    def handler(args: dict[str, Any], **_kwargs: Any) -> str:
        model = args.get("model") or DEFAULTS[operation]
        family = families.get(model)
        if family is None:
            return _error(f"model must be one of: {', '.join(families)}.", "invalid_argument")
        key = get_fal_key()
        if not key:
            return _error("FAL_KEY is not configured.", "auth_required", model)
        client = make_client(key)
        max_bytes = _int_setting(get_config, "max_upload_mb", 200, 1, 2048) * 1024 * 1024
        timeout = _int_setting(get_config, "timeout_seconds", 900, 60, 3600)

        refs = args.get("reference_image_urls") or []
        video_refs = args.get("reference_video_urls") or []
        for name, value in (("reference_image_urls", refs), ("reference_video_urls", video_refs)):
            if not isinstance(value, list):
                return _error(f"{name} must be a list.", "invalid_argument", model)
        try:
            request = Request(
                prompt=args.get("prompt") or "",
                video_url=args.get("video_url") or None,
                reference_urls=tuple(refs),
                video_reference_urls=tuple(video_refs),
                resolution=args.get("resolution"), aspect_ratio=args.get("aspect_ratio"),
                duration=args.get("duration"), seed=args.get("seed"), audio=args.get("audio"),
                keep_audio=args.get("keep_audio"),
            )
            # Reject bad arguments before uploading anything.
            build_payload(operation, model, family, request)
            video = (media.prepare(request.video_url, "video", client, max_bytes)
                     if request.video_url else None)
            images = tuple(media.prepare(ref, "image", client, max_bytes) for ref in refs)
            videos = tuple(media.prepare(ref, "video", client, max_bytes) for ref in video_refs)
            payload = build_payload(operation, model, family, replace(
                request, video_url=video, reference_urls=images, video_reference_urls=videos))
        except (InvalidRequest, media.MediaError) as exc:
            return _error(str(exc), "invalid_argument", model)
        except Exception as exc:
            logger.warning("FAL upload failed: %s", exc)
            return _error(f"Uploading media to FAL failed: {exc}", "upload_failed", model)

        try:
            result = runner.run(client, family.endpoint, payload, timeout)
        except runner.FalTimeout as exc:
            return _error(str(exc), "timeout", model)
        except Exception as exc:
            logger.warning("FAL %s failed (%s): %s", operation, family.endpoint, exc)
            return _error(f"FAL video {operation} failed: {exc}", "api_error", model)
        url, extra = runner.video_url(result)
        if not url:
            return _error("FAL returned no video URL.", "empty_response", model)
        return json.dumps({
            "success": True, "video": url, "model": model, "endpoint": family.endpoint,
            "operation": operation, "prompt": payload["prompt"], "provider": "fal", **extra,
        })

    return handler


def tool_specs(get_config: ConfigGetter) -> list[dict[str, Any]]:
    specs = []
    for operation in OPERATIONS:
        schema = _schema(operation)
        specs.append({
            "name": schema["name"], "toolset": TOOLSET, "schema": schema,
            "handler": make_handler(operation, get_config), "check_fn": is_available,
            "requires_env": [FAL_KEY_ENV], "emoji": "🎬", "description": schema["description"],
        })
    return specs
