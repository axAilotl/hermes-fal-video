"""FAL endpoints per operation, checked against each endpoint's published OpenAPI input schema.

Every value the tools accept is listed here, so a request that would be rejected by FAL is
rejected locally with the allowed values instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Family:
    endpoint: str
    display: str
    resolutions: tuple[str, ...] = ()  # FAL's own spelling; matched case-insensitively
    aspect_ratios: tuple[str, ...] = ()
    duration_range: tuple[int, int] | None = None
    duration_as_string: bool = False  # Seedance's queue schema takes "4".."15" strings
    duration_auto: bool = False  # "auto" accepted in place of a number
    reference_key: str = ""  # payload key for reference images
    max_references: int = 0
    references_required: bool = False  # the endpoint rejects a request without images
    video_reference_key: str = ""  # payload key for reference videos
    max_video_references: int = 0
    seed: bool = False
    audio_key: str = ""  # payload key of the generate-audio switch
    keep_audio: bool = False  # video edit: audio_setting="origin" keeps the source track
    fixed: tuple[tuple[str, Any], ...] = ()  # values the endpoint requires on every request
    notes: str = ""


_KLING_ASPECTS = ("auto", "16:9", "9:16", "1:1", "21:9")
_GEMINI_RESOLUTIONS = ("360p", "720p", "1080p", "4k")
_H3_ASPECTS = ("adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
_H3_MAX_EXTEND_ASPECTS = ("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
_WAN3_ASPECTS = ("adaptive", "16:9", "4:3", "1:1", "3:4", "9:16")
_SEEDANCE_ASPECTS = ("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
_FLUX3_ASPECTS = ("auto", "21:9", "2:1", "16:9", "4:3", "1:1", "3:4", "9:16")
_GROK_ASPECTS = ("16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16")
_TAGS = "Refer to references in the prompt as @Image1, @Video1, ..."


def _h3_max(endpoint: str, display: str, notes: str) -> Family:
    return Family(
        endpoint=endpoint,
        display=display,
        resolutions=("480P", "768P", "1080P"),
        aspect_ratios=_H3_ASPECTS,
        duration_range=(1, 15),
        reference_key="reference_image_urls",
        max_references=9,
        video_reference_key="reference_video_urls",
        max_video_references=3,
        seed=True,
        fixed=(("prompt_expansion_mode", "balanced"),),
        notes=notes,
    )


def _h3_max_extend(endpoint: str, display: str, notes: str) -> Family:
    return Family(
        endpoint=endpoint,
        display=display,
        resolutions=("480P", "768P", "1080P", "2K"),
        aspect_ratios=_H3_MAX_EXTEND_ASPECTS,
        duration_range=(1, 15),
        seed=True,
        notes=notes,
    )


def _wan3(endpoint: str, display: str, notes: str) -> Family:
    return Family(
        endpoint=endpoint,
        display=display,
        resolutions=("480p", "720p", "1080p"),
        aspect_ratios=_WAN3_ASPECTS,
        duration_range=(2, 30),
        reference_key="reference_image_urls",
        max_references=10,
        video_reference_key="reference_video_urls",
        max_video_references=5,
        seed=True,
        audio_key="audio",
        notes=notes,
    )


def _seedance2(endpoint: str, display: str, resolutions: tuple[str, ...], notes: str) -> Family:
    return Family(
        endpoint=endpoint,
        display=display,
        resolutions=resolutions,
        aspect_ratios=_SEEDANCE_ASPECTS,
        duration_range=(4, 15),
        duration_as_string=True,
        duration_auto=True,
        reference_key="image_urls",
        max_references=9,
        video_reference_key="video_urls",
        max_video_references=3,
        audio_key="generate_audio",
        notes=notes,
    )


EDIT: dict[str, Family] = {
    "kling-v4": Family(
        endpoint="kling/v4/video-to-video/edit",
        display="Kling 4.0",
        resolutions=("720p", "1080p"),
        aspect_ratios=_KLING_ASPECTS,
        duration_range=(3, 30),
        reference_key="image_urls",
        max_references=10,
        video_reference_key="video_urls",
        max_video_references=4,
        notes=f"Edit with up to 10 image and 4 video references, 3-30 s. {_TAGS}",
    ),
    "kling-v4-flash": Family(
        endpoint="kling/v4/flash/video-to-video",
        display="Kling 4.0 Flash",
        resolutions=("720p",),
        duration_range=(3, 20),
        reference_key="image_urls",
        max_references=10,
        video_reference_key="video_urls",
        max_video_references=4,
        notes="Faster, cheaper Kling 4.0 edit at 720p, 3-20 s.",
    ),
    "gemini-omni-flash": Family(
        endpoint="google/gemini-omni-flash/v1.2/edit",
        display="Gemini Omni Flash 1.2",
        resolutions=_GEMINI_RESOLUTIONS,
        notes="Prompted edit of a clip, up to 4k.",
    ),
    "flux-3": Family(
        endpoint="blackforestlabs/flux-3/edit-video",
        display="FLUX 3 Fast",
        notes="Fast prompted edit; keeps the source length and framing.",
    ),
    "grok-imagine": Family(
        endpoint="xai/grok-imagine-video/edit-video",
        display="Grok Imagine",
        resolutions=("auto", "480p", "720p"),
        notes="Prompted restyle or change of an existing clip.",
    ),
    "happy-horse": Family(
        endpoint="alibaba/happy-horse/video-edit",
        display="Happy Horse",
        resolutions=("720p", "1080p"),
        reference_key="reference_image_urls",
        max_references=5,
        seed=True,
        keep_audio=True,
        notes="Edit guided by up to 5 reference images; can keep the source audio.",
    ),
}

EXTEND: dict[str, Family] = {
    "h3-max": _h3_max_extend(
        "minimax/h3-max/extend-video", "MiniMax H3 Max", "Continues the clip for 1-15 s, up to 2K."
    ),
    "h3-max-turbo": _h3_max_extend(
        "minimax/h3-max-turbo/extend-video",
        "MiniMax H3 Max Turbo",
        "Faster H3 Max extension, 1-15 s.",
    ),
    "flux-3": Family(
        endpoint="blackforestlabs/flux-3/extend-video",
        display="FLUX 3",
        resolutions=("720p", "1080p", "1440p", "2160p"),
        aspect_ratios=_FLUX3_ASPECTS,
        duration_range=(5, 20),
        duration_auto=True,
        audio_key="generate_audio",
        notes="Continues the clip for 5-20 s (or auto), up to 2160p, with audio.",
    ),
    "flux-3-draft": Family(
        endpoint="blackforestlabs/flux-3/extend-video/draft",
        display="FLUX 3 Draft",
        aspect_ratios=_FLUX3_ASPECTS,
        duration_range=(5, 20),
        duration_auto=True,
        audio_key="generate_audio",
        notes="Cheap low-resolution FLUX 3 preview of an extension.",
    ),
    "gemini-omni-flash": Family(
        endpoint="google/gemini-omni-flash/v1.2/extend",
        display="Gemini Omni Flash 1.2",
        resolutions=_GEMINI_RESOLUTIONS,
        duration_range=(3, 10),
        notes="Continues the clip for 3-10 s, up to 4k.",
    ),
    "pixverse-v6": Family(
        endpoint="fal-ai/pixverse/v6/extend",
        display="PixVerse V6",
        resolutions=("360p", "540p", "720p", "1080p"),
        duration_range=(1, 15),
        seed=True,
        audio_key="generate_audio_switch",
        notes="Continues the clip for 1-15 s, optional audio.",
    ),
    "grok-imagine": Family(
        endpoint="xai/grok-imagine-video/extend-video",
        display="Grok Imagine",
        duration_range=(2, 10),
        notes="Continues the clip for 2-10 seconds.",
    ),
}

REFERENCE: dict[str, Family] = {
    "h3-max": _h3_max(
        "minimax/h3-max/reference-to-video",
        "MiniMax H3 Max",
        f"Up to 9 image and 3 video references, 1-15 s. {_TAGS}",
    ),
    "h3-max-turbo": _h3_max(
        "minimax/h3-max-turbo/reference-to-video",
        "MiniMax H3 Max Turbo",
        "Faster H3 Max, same references and lengths.",
    ),
    "h3": Family(
        endpoint="minimax/h3/reference-to-video",
        display="MiniMax H3",
        resolutions=("480P", "768P", "2K", "4K"),
        aspect_ratios=_H3_ASPECTS,
        duration_range=(5, 15),
        reference_key="reference_image_urls",
        max_references=9,
        video_reference_key="reference_video_urls",
        max_video_references=3,
        seed=True,
        notes="Up to 9 image and 3 video references, 5-15 s, up to 4K.",
    ),
    "kling-v4": Family(
        endpoint="kling/v4/reference-to-video",
        display="Kling 4.0",
        resolutions=("720p", "1080p"),
        aspect_ratios=_KLING_ASPECTS,
        duration_range=(3, 30),
        reference_key="image_urls",
        max_references=10,
        video_reference_key="video_urls",
        max_video_references=5,
        notes=f"Up to 10 image and 5 video references, 3-30 s. {_TAGS}",
    ),
    "kling-v4-flash": Family(
        endpoint="kling/v4/flash/reference-to-video",
        display="Kling 4.0 Flash",
        resolutions=("720p",),
        aspect_ratios=_KLING_ASPECTS,
        duration_range=(3, 20),
        reference_key="image_urls",
        max_references=10,
        video_reference_key="video_urls",
        max_video_references=5,
        notes="Faster, cheaper Kling 4.0 at 720p, 3-20 s.",
    ),
    "seedance-2.5": Family(
        endpoint="bytedance/seedance-2.5/us/reference-to-video",
        display="Seedance 2.5",
        resolutions=("480p", "720p", "1080p"),
        aspect_ratios=_SEEDANCE_ASPECTS,
        duration_range=(4, 30),
        duration_as_string=True,
        duration_auto=True,
        reference_key="image_urls",
        max_references=30,
        video_reference_key="video_urls",
        max_video_references=10,
        seed=True,
        audio_key="generate_audio",
        notes=f"Up to 30 image and 10 video references, 4-30 s, optional audio. {_TAGS}",
    ),
    "seedance-2.0": _seedance2(
        "bytedance/seedance-2.0/us/reference-to-video",
        "Seedance 2.0",
        ("480p", "720p", "1080p", "4k"),
        "Up to 9 image and 3 video references, 4-15 s, up to 4k.",
    ),
    "seedance-2.0-fast": _seedance2(
        "bytedance/seedance-2.0/fast/reference-to-video",
        "Seedance 2.0 Fast",
        ("480p", "720p"),
        "Faster, cheaper Seedance 2.0 up to 720p.",
    ),
    "wan-3.0": _wan3(
        "alibaba/wan-3.0/reference-to-video",
        "Wan 3.0",
        "Up to 10 image and 5 video references, 2-30 s, optional audio.",
    ),
    "wan-3.0-prime": _wan3(
        "alibaba/wan-3.0-prime/reference-to-video",
        "Wan 3.0 Prime",
        "Higher-quality Wan 3.0, same references and lengths.",
    ),
    "gemini-omni-flash": Family(
        endpoint="google/gemini-omni-flash/v1.2/reference-to-video",
        display="Gemini Omni Flash 1.2",
        resolutions=_GEMINI_RESOLUTIONS,
        aspect_ratios=("16:9", "9:16"),
        duration_range=(3, 15),
        reference_key="image_urls",
        max_references=10,
        video_reference_key="reference_video_urls",
        max_video_references=3,
        notes="Up to 10 image and 3 video references, 3-15 s, up to 4k.",
    ),
    "vidu-q4": Family(
        endpoint="fal-ai/vidu/q4/reference-to-video",
        display="Vidu Q4",
        resolutions=("540p", "720p", "1080p", "2K", "4K"),
        aspect_ratios=("16:9", "9:16", "4:3", "3:4", "1:1"),
        duration_range=(3, 16),
        reference_key="reference_image_urls",
        max_references=12,
        seed=True,
        audio_key="audio",
        notes="Up to 12 image references, 3-16 s, up to 4K.",
    ),
    "happy-horse": Family(
        endpoint="alibaba/happy-horse/v1.1/reference-to-video",
        display="Happy Horse 1.1",
        resolutions=("720p", "1080p"),
        aspect_ratios=("16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21", "5:4", "4:5"),
        duration_range=(3, 15),
        reference_key="image_urls",
        max_references=9,
        references_required=True,
        seed=True,
        notes="Up to 9 image references, 3-15 s, native audio.",
    ),
    "grok-imagine": Family(
        endpoint="xai/grok-imagine-video/v1.5/reference-to-video",
        display="Grok Imagine 1.5",
        resolutions=("480p", "720p"),
        aspect_ratios=_GROK_ASPECTS,
        duration_range=(1, 15),
        reference_key="reference_image_urls",
        max_references=7,
        references_required=True,
        notes="Up to 7 image references, 1-15 s.",
    ),
}

OPERATIONS: dict[str, dict[str, Family]] = {"edit": EDIT, "extend": EXTEND, "reference": REFERENCE}
DEFAULTS = {"edit": "kling-v4", "extend": "h3-max", "reference": "h3-max"}
