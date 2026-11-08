"""FAL endpoints per operation, checked against each endpoint's published OpenAPI input schema.

Every value the tools accept is listed here, so a request that would be rejected by FAL is
rejected locally with the allowed values instead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    endpoint: str
    display: str
    resolutions: tuple[str, ...] = ()
    aspect_ratios: tuple[str, ...] = ()
    duration_range: tuple[int, int] | None = None
    duration_as_string: bool = False  # Seedance's queue schema takes "4".."15" strings
    duration_auto: bool = False  # "auto" accepted in place of a number
    reference_key: str = ""  # payload key for reference images
    max_references: int = 0
    seed: bool = False
    audio_toggle: bool = False  # exposes generate_audio
    keep_audio: bool = False  # video edit: audio_setting="origin" keeps the source track
    notes: str = ""


EDIT: dict[str, Family] = {
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
    "grok-imagine": Family(
        endpoint="xai/grok-imagine-video/extend-video",
        display="Grok Imagine",
        duration_range=(2, 10),
        notes="Continues the clip for 2-10 seconds.",
    ),
}

REFERENCE: dict[str, Family] = {
    "seedance-2.0": Family(
        endpoint="bytedance/seedance-2.0/reference-to-video",
        display="Seedance 2.0",
        resolutions=("480p", "720p", "1080p", "4k"),
        aspect_ratios=("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"),
        duration_range=(4, 15),
        duration_as_string=True,
        duration_auto=True,
        reference_key="image_urls",
        max_references=9,
        audio_toggle=True,
        notes="Up to 9 references, 4-15 s, optional generated audio.",
    ),
    "happy-horse": Family(
        endpoint="alibaba/happy-horse/reference-to-video",
        display="Happy Horse",
        resolutions=("720p", "1080p"),
        aspect_ratios=("16:9", "9:16", "1:1", "4:3", "3:4"),
        duration_range=(3, 15),
        reference_key="image_urls",
        max_references=9,
        seed=True,
        notes="Up to 9 references, 3-15 s, native audio.",
    ),
    "grok-imagine": Family(
        endpoint="xai/grok-imagine-video/reference-to-video",
        display="Grok Imagine",
        resolutions=("480p", "720p"),
        aspect_ratios=("16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16"),
        duration_range=(1, 10),
        reference_key="reference_image_urls",
        max_references=7,
        notes="Up to 7 references, 1-10 s.",
    ),
}

OPERATIONS: dict[str, dict[str, Family]] = {"edit": EDIT, "extend": EXTEND, "reference": REFERENCE}
DEFAULTS = {"edit": "grok-imagine", "extend": "grok-imagine", "reference": "seedance-2.0"}
