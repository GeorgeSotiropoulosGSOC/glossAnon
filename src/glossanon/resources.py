"""Helpers for loading packaged data files (dictionaries, suffix lists).

Uses :mod:`importlib.resources` so the lists load correctly whether the package
is installed as a wheel, run from source, or zipped.
"""

from __future__ import annotations

from importlib import resources
from typing import List


def load_lines(filename: str) -> List[str]:
    """Load non-empty, non-comment lines from ``glossanon/data/<filename>``.

    Lines are stripped; blank lines and lines starting with ``#`` are skipped.
    Returns an empty list if the file is missing (the recognizers fall back to
    built-in defaults in that case).
    """
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
