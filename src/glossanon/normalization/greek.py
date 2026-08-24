"""Greek alphabet constants and small text helpers.

These are shared building blocks for the recognizers (especially name
detection) and the OCR pass. Everything is plain-Python and standard-library
only.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache

# Lowercase, with accents/diaeresis and final sigma.
GREEK_LOWER = "αβγδεζηθικλμνξοπρστυφχψωάέήίόύώϊϋΐΰ" + "ς"
# Uppercase, with accents/diaeresis.
GREEK_UPPER = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΆΈΉΊΌΎΏΪΫ"

GREEK_LETTERS = GREEK_LOWER + GREEK_UPPER
_GREEK_UPPER_SET = frozenset(GREEK_UPPER)
_GREEK_SET = frozenset(GREEK_LETTERS)


def is_greek_char(ch: str) -> bool:
    """True if ``ch`` is a Greek letter (any case, accented or not)."""
    return ch in _GREEK_SET


def is_greek_upper(ch: str) -> bool:
    """True if ``ch`` is an uppercase Greek letter (accented or not)."""
    return ch in _GREEK_UPPER_SET


# Hot path: the name heuristics fold the same token several times over.
@lru_cache(maxsize=8192)
def strip_accents(text: str) -> str:
    """Remove Greek diacritics, preserving length and case.

    ``"Παπαδόπουλος" -> "Παπαδοπουλος"``. Used for case/accent-insensitive
    dictionary lookups (matching inflected, accented name forms). The result
    has the same number of characters as the input because Greek accents are
    combining marks over a single base letter.
    """
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", without_marks)


@lru_cache(maxsize=8192)
def fold(text: str) -> str:
    """Aggressive fold for lookups: lower-cased and accent-stripped.

    Note: this may change length for letters whose lowercase maps to multiple
    code points, so it must only be used for *comparison keys*, never for
    building the output text.
    """
    return strip_accents(text).lower()


# Treat ς and σ as equal when comparing tokens.
def normalize_sigma(text: str) -> str:
    return text.replace("ς", "σ")
