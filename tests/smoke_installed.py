"""Run after installing the built wheel, from outside the source import path."""

import importlib
import os
import tempfile
from pathlib import Path

import yaml
from hermes_cli.plugins import PluginManager
from tools.registry import registry

PLUGIN = "hermes-fal-video"
module = importlib.import_module("hermes_fal_video")
assert not Path(module.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[1])
assert (Path(module.__file__).parent / "skills" / "fal-video-pipeline" / "SKILL.md").is_file()
with tempfile.TemporaryDirectory() as temporary:
    os.environ["HERMES_HOME"] = temporary
    os.environ["FAL_KEY"] = "smoke-test-key"
    (Path(temporary) / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [PLUGIN]}}), encoding="utf-8"
    )
    manager = PluginManager()
    try:
        manager.discover_and_load()
        loaded = manager._plugins[PLUGIN]
        assert loaded.enabled and not loaded.error, loaded.error
        for name in ("fal_video_edit", "fal_video_extend", "fal_video_from_references"):
            entry = registry.get_entry(name)
            assert entry is not None and entry.check_fn(), name
        assert manager.find_plugin_skill(f"{PLUGIN}:fal-video-pipeline") is not None
        print(f"Installed wheel discovered and registered: {PLUGIN}")
    finally:
        manager.unload()
