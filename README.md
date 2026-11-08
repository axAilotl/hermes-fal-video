# Hermes FAL Video

Video edit, video extend, and reference-to-video on [FAL](https://fal.ai) for
[Hermes Agent](https://github.com/NousResearch/hermes-agent), plus a skill
that chains them. A standalone plugin.

Hermes' own `video_generate` covers text-to-video and image-to-video across
providers and deliberately leaves out edit and extend, because those
operations differ too much between backends for one tool. This plugin adds
them for FAL as separate tools, the same way Hermes ships xAI's edit/extend.

| Tool | Models | What it does |
| --- | --- | --- |
| `fal_video_edit` | `grok-imagine` (default), `happy-horse` | Change an existing clip with a prompt; Happy Horse also takes up to 5 reference images and can keep the source audio. |
| `fal_video_extend` | `grok-imagine` | Continue a clip for 2-10 s. |
| `fal_video_from_references` | `seedance-2.0` (default), `happy-horse`, `grok-imagine` | New clip featuring the people/products in up to 9 (Grok: 7) reference images. |

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

## Configure

Optional settings under `plugins.entries.hermes-fal-video.settings`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `timeout_seconds` | `900` | Wait for one FAL job this long (60-3600), then cancel it. |
| `max_upload_mb` | `200` | Largest local file uploaded to FAL storage. |

## Behaviour

- **Validation first.** Every argument is checked against the chosen model
  before anything is uploaded or submitted. Errors list the accepted values
  (for example `grok-imagine resolution must be one of: auto, 480p, 720p`).
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
