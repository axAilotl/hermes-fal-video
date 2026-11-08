---
name: fal-video-pipeline
description: Edit, extend, and make videos from references on FAL.
version: 1.0.0
author: axAilotl (@axAilotl), Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Creative, Media, FAL, Video]
    category: creative
    requires_tools: [fal_video_edit, fal_video_extend, fal_video_from_references]
---

# FAL Video Pipeline Skill

Plans multi-step video work on FAL: building a clip from reference images,
editing an existing clip, and extending it. It chooses the tool and model for
each step and keeps the URLs chained. It does not configure FAL or judge the
output for the user.

## When to Use

- The user wants to change an existing video (restyle, replace an object,
  relight) rather than generate a new one.
- The user wants a clip to keep going past its last frame.
- The user has photos of a person, product or character and wants them to
  appear in a new video.
- A concept-to-video request where a still image should be fixed before it is
  animated.

## Prerequisites

- The `hermes-fal-video` plugin is enabled and `FAL_KEY` is set; the three
  `fal_video_*` tools only appear when it is.
- For first frames and plain image-to-video, `image_generate` and
  `video_generate` configured for any provider.

## How to Run

Call the tools directly. Local paths are uploaded to FAL storage for you;
HTTPS URLs are passed through. Each call takes one to ten minutes.

## Quick Reference

| Goal | Tool | Model |
| --- | --- | --- |
| Video from reference photos | `fal_video_from_references` | `seedance-2.0` (default, audio, up to 9 refs), `happy-horse` (1080p), `grok-imagine` (fast, up to 7 refs) |
| Restyle or change a clip | `fal_video_edit` | `grok-imagine` (default), `happy-horse` (reference-guided, `keep_audio`) |
| Make a clip longer | `fal_video_extend` | `grok-imagine`, 2-10 s per call |
| First frame | `image_generate` | any |
| Animate one still | `video_generate` | any |

## Procedure

1. Restate the goal in one sentence: subject, length, aspect ratio, audio, and
   whether a source clip or reference photos already exist.
2. No footage and no references: make a first frame with `image_generate`,
   inspect it, fix framing or text with another `image_generate` call that
   passes it as `image_url`, then animate it with `video_generate`.
3. Reference photos of a subject: call `fal_video_from_references` with the
   photos in `reference_image_urls` and a prompt that names what each one is
   ("the woman in image 1 hands the bottle in image 2 to ...").
4. To change a clip, call `fal_video_edit` with its `video_url`. Use
   `happy-horse` with `reference_image_urls` when the change must match a
   specific look, and `keep_audio: true` to keep the original sound.
5. To lengthen a clip, call `fal_video_extend` with the latest `video` URL and
   a prompt describing only what happens next. Repeat for more length; each
   call continues the previous output.
6. Pass each step's returned `video` URL straight into the next step. Do not
   download and re-upload it.
7. Report every output URL, the model and the exact prompt for each step so
   the user can iterate on one step without redoing the others.

## Pitfalls

- Error messages list the values a model accepts. Read them and retry with an
  allowed value instead of switching tools.
- Only `seedance-2.0` takes `audio`; `happy-horse` and `grok-imagine`
  generate their own soundtrack.
- Seedance and Happy Horse reference clips are slow and priced per second;
  confirm length before a long request.
- Local files must have a media extension and are uploaded to FAL storage.
  Do not pass anything the user would not want leaving the machine.
- A timeout error includes the FAL request ID; tell the user rather than
  silently resubmitting, since the first job may still be billed.

## Verification

Each successful call returns `success: true` and a `video` HTTPS URL. Check
one step on a short clip before chaining several, for example a 4 s
`fal_video_from_references` request at `480p`.
