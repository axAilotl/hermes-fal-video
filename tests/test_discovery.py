"""Real Hermes path: manifest scan, namespaced import, tool and skill registration, gating."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

PLUGIN = "hermes-fal-video"
REPO = Path(__file__).resolve().parents[1]
TOOLS = ["fal_video_edit", "fal_video_extend", "fal_video_from_references"]


def _install(tmp_path, monkeypatch) -> None:
    home = tmp_path / "hermes"
    (home / "plugins").mkdir(parents=True)
    shutil.copytree(REPO, home / "plugins" / PLUGIN, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"))
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [PLUGIN]}}), encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))


def test_real_discovery_registers_gated_tools_and_skill(tmp_path, monkeypatch) -> None:
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    monkeypatch.delenv("FAL_KEY", raising=False)
    _install(tmp_path, monkeypatch)
    manager = PluginManager()
    try:
        manager.discover_and_load()
        loaded = manager._plugins[PLUGIN]
        assert loaded.enabled and loaded.error is None, loaded.error
        assert sorted(loaded.tools_registered) == TOOLS
        entries = [registry.get_entry(name) for name in TOOLS]
        assert all(entry is not None and entry.toolset == "fal_video" for entry in entries)
        assert not any(entry.check_fn() for entry in entries)
        monkeypatch.setenv("FAL_KEY", "fal-test-key")
        assert all(entry.check_fn() for entry in entries)
        assert manager.find_plugin_skill(f"{PLUGIN}:fal-video-pipeline") is not None
    finally:
        manager.unload()


def test_manifest_declares_exactly_the_registered_tools() -> None:
    manifest = yaml.safe_load((REPO / "plugin.yaml").read_text(encoding="utf-8"))
    assert sorted(manifest["provides_tools"]) == TOOLS


def test_skill_meets_authoring_standards() -> None:
    text = (REPO / "hermes_fal_video/skills/fal-video-pipeline/SKILL.md").read_text("utf-8")
    description = re.search(r"^description: (.*)$", text, re.MULTILINE).group(1)
    assert len(description) <= 60 and description.endswith(".")
    sections = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert sections == ["When to Use", "Prerequisites", "How to Run", "Quick Reference",
                        "Procedure", "Pitfalls", "Verification"]
