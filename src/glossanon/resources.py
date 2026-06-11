from __future__ import annotations

from importlib import resources
from typing import List


def load_lines(filename: str) -> List[str]:

    try:
        text = resources.files("glossanon.data").joinpath(filename).read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError):  # pragma: no cover
        return []

    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines
