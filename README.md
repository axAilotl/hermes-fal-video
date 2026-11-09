# Hermes FAL Video

Video edit, video extend, and reference-to-video on [FAL](https://fal.ai) for
[Hermes Agent](https://github.com/NousResearch/hermes-agent), plus a skill
that chains them. A standalone plugin.

Hermes' own `video_generate` covers text-to-video and image-to-video across
providers and deliberately leaves out edit and extend, because those
operations differ too much between backends for one tool. This plugin adds
them for FAL as separate tools, the same way Hermes ships xAI's edit/extend.

| Tool | What it does |
| --- | --- |
| `fal_video_edit` | Change an existing clip with a prompt, optionally guided by reference images or videos. |
| `fal_video_extend` | Continue a clip past its last frame. |
| `fal_video_from_references` | New clip featuring the people, products or motion in reference images and videos. |

Models (checked against fal's catalog and published input schemas, November 2026):

| Tool | `model` | FAL model | Notes |
| --- | --- | --- | --- |
| edit | `kling-v4` (default) | Kling 4.0 Video Edit | 720p/1080p, 3-30 s, up to 10 image + 4 video refs |
| edit | `kling-v4-flash` | Kling 4.0 Flash | 720p, 3-20 s, cheaper |
| edit | `gemini-omni-flash` | Gemini Omni Flash 1.2 | 360p-4k |
| edit | `flux-3` | FLUX 3 Fast Edit | prompt only, fast |
| edit | `grok-imagine` | Grok Imagine | up to 720p |
| edit | `happy-horse` | Happy Horse | up to 5 image refs, `keep_audio` |
| extend | `h3-max` (default) | MiniMax H3 Max | 1-15 s, up to 2K |
| extend | `h3-max-turbo` | MiniMax H3 Max Turbo | faster H3 Max |
| extend | `flux-3` | FLUX 3 Extend | 5-20 s or auto, up to 2160p, audio |
| extend | `flux-3-draft` | FLUX 3 Extend Draft | cheap preview |
| extend | `gemini-omni-flash` | Gemini Omni Flash 1.2 | 3-10 s, up to 4k |
| extend | `pixverse-v6` | PixVerse V6 | 1-15 s, audio |
| extend | `grok-imagine` | Grok Imagine | 2-10 s |
| references | `h3-max` (default) | MiniMax H3 Max | 1-15 s, 9 image + 3 video refs |
| references | `h3-max-turbo` | MiniMax H3 Max Turbo | faster H3 Max |
| references | `h3` | MiniMax H3 | 5-15 s, up to 4K |
| references | `kling-v4` | Kling 4.0 | 3-30 s, 10 image + 5 video refs |
| references | `kling-v4-flash` | Kling 4.0 Flash | 720p, 3-20 s |
| references | `seedance-2.5` | Seedance 2.5 | 4-30 s, 30 image + 10 video refs, audio |
| references | `seedance-2.0` | Seedance 2.0 | 4-15 s, up to 4k, audio |
| references | `seedance-2.0-fast` | Seedance 2.0 Fast | up to 720p |
| references | `wan-3.0` | Wan 3.0 | 2-30 s, 10 image + 5 video refs, audio |
| references | `wan-3.0-prime` | Wan 3.0 Prime | higher-quality Wan 3.0 |
| references | `gemini-omni-flash` | Gemini Omni Flash 1.2 | 3-15 s, 16:9/9:16, up to 4k |
| references | `vidu-q4` | Vidu Q4 | 3-16 s, 12 image refs, up to 4K |
| references | `happy-horse` | Happy Horse 1.1 | 3-15 s, 9 image refs |
| references | `grok-imagine` | Grok Imagine 1.5 | 1-15 s, 7 image refs |

Each model's exact resolutions, aspect ratios and durations are in
`hermes_fal_video/families.py`. Resolutions are matched case-insensitively,
and `auto` and `adaptive` aspect ratios are treated as the same thing.

The bundled `fal-video-pipeline` skill (`skill_view("hermes-fal-video:fal-video-pipeline")`)
tells the agent when to use which tool and how to chain outputs.

## Requirements

- Hermes **0.23.0 or newer**.
- A FAL API key (`FAL_KEY`). The managed Nous tool gateway is not used: Hermes
  does not expose it to plugins.

## Install

```sh
hermes plugins install axAilotl/hermes-fal-video --enable
hermes config set FAL_KEY fal-...      # stored in the profile's .env
```

Accept the dependency prompt (`fal-client`). The `fal_video` toolset is on by
default once the plugin is enabled; its tools only appear to the model when
`FAL_KEY` is set. Toggle it per platform in `hermes tools`.

In multiplex mode, the active profile's secret scope must contain `FAL_KEY`.
With no scope or no scoped key, the tools stay unavailable and requests return
`auth_required`; they never borrow a key from the process environment.

## Configure

Optional settings under `plugins.entries.hermes-fal-video.settings`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `timeout_seconds` | `900` | Wait for one FAL job this long (60-3600), then cancel it. |
| `max_upload_mb` | `200` | Largest local file uploaded to FAL storage. |

## Behaviour

- **Validation first.** Every argument is checked against the chosen model
  before anything is uploaded or submitted. Errors list the accepted values
  (for example `kling-v4 resolution must be one of: 720p, 1080p`).
  The accepted values come from each endpoint's published FAL input schema.
- **Local files.** HTTPS URLs are passed to FAL as-is. Local paths and
  `file://` URLs are uploaded to FAL storage, but only regular files whose
  real (symlink-resolved) name has a media extension: `.mp4 .mov .webm .m4v
  .mkv` for video, `.png .jpg .jpeg .webp .gif` for images. That keeps the
  tools from uploading arbitrary files such as credentials. Paths are read on
  the machine running Hermes, so this suits the local terminal backend.
- **Timeouts.** A job still running at `timeout_seconds` is cancelled and the
  error includes its FAL request ID.
- **Output.** A successful call returns `{"success": true, "video": "<https url>", ...}`
  with the model, endpoint and any size/duration metadata FAL reports.

## Privacy

Prompts and media go to FAL, which bills the account behind `FAL_KEY`. The
plugin stores nothing itself; Hermes keeps tool results in conversation
history as usual.

## Testing and development

CI tests Hermes v0.23.0 on Linux, macOS and Windows, plus Hermes main on
Linux: payload validation for every model, the local-file guard (including
symlinks), the polling/timeout/cancel loop, handler error paths, schema
coverage of every model's values, real plugin discovery with key gating, and
the bundled skill. No test calls FAL.

```sh
git clone --branch v0.23.0 --depth 1 https://github.com/NousResearch/hermes-agent.git ../hermes-agent
python -m pip install --no-deps -e ../hermes-agent
python -m pip install -r tests/requirements-host.txt '.[dev]' build
python -m pytest -q
ruff check .
hermes plugins doctor . --ci
hermes plugins validate .
```

## License

MIT
