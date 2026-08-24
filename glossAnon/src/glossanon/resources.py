"""Helpers for loading packaged data files (dictionaries, suffix lists).

Uses :mod:`importlib.resources` so the lists load correctly whether the package
is installed as a wheel, run from source, or zipped.

Loading failures are raised, never swallowed. The recognizers build their whole
lookup vocabulary from these files, so an empty list would silently degrade
detection to near-zero recall while still reporting a clean run - the worst
possible failure mode for an anonymizer.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import List, Tuple

_PACKAGE = "glossanon"
_DATA_DIR = "data"


class MissingResourceError(RuntimeError):
    """A packaged data file could not be read.

    Signals a broken or incomplete installation. Raised loudly on purpose: see
    the module docstring for why silence would be dangerous here.
    """


@lru_cache(maxsize=None)
def _read_lines(filename: str) -> Tuple[str, ...]:
    """Read and parse a data file once per process (results are cached)."""
    # Anchored on the package, so data/ need not be importable.
    try:
        text = (
            resources.files(_PACKAGE)
            .joinpath(_DATA_DIR, filename)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise MissingResourceError(
            f"could not read packaged data file '{_PACKAGE}/{_DATA_DIR}/{filename}' "
            f"({type(exc).__name__}: {exc}). The installation looks incomplete - "
            "reinstall the package so its data/ directory ships with it."
        ) from exc

    return tuple(
        line
        for line in (raw.strip() for raw in text.splitlines())
        if line and not line.startswith("#")
    )


def load_lines(filename: str) -> List[str]:
    """Load non-empty, non-comment lines from ``glossanon/data/<filename>``.

    Lines are stripped; blank lines and lines starting with ``#`` are skipped.
    The parsed file is cached, so repeated recognizer construction is cheap.

    Raises:
        MissingResourceError: if the file is missing or unreadable.
    """
    # Fresh list per call, so a caller cannot mutate the cache.
    return list(_read_lines(filename))
