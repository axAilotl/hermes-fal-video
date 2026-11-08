"""Hermes registration entry point for the FAL video edit/extend/reference plugin."""

from __future__ import annotations

from pathlib import Path

from .tools import tool_specs

SKILLS_DIR = Path(__file__).parent / "skills"


def register(ctx) -> None:
    for spec in tool_specs(ctx.get_config):
        ctx.register_tool(**spec)
    for child in sorted(SKILLS_DIR.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.is_file():
            ctx.register_skill(child.name, skill_md)


__all__ = ["register"]
