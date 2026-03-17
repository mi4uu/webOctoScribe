from __future__ import annotations

import os
from pathlib import Path
from minijinja import Environment

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _loader(name: str) -> str | None:
    path = TEMPLATE_DIR / name
    if path.exists():
        return path.read_text()
    return None


env = Environment(loader=_loader)


def render(template_name: str, **kwargs) -> str:
    return env.render_template(template_name, **kwargs)
