"""Text normalization utilities.

Two concerns live here:

* :mod:`glossanon.normalization.greek` - Greek alphabet constants and helpers
  (character classes, accent stripping, casing) used across recognizers.
* :mod:`glossanon.normalization.ocr` - a *length-preserving* OCR repair pass
  that fixes common scanning mistakes (Latin/Greek look-alike characters,
  exotic whitespace) without shifting any character offsets.

The length-preserving guarantee is central: recognizers can run detection on a
normalized "view" of the text while every reported ``(start, end)`` offset
still maps exactly onto the original input.
"""

from .greek import (
    GREEK_LETTERS,
    GREEK_LOWER,
    GREEK_UPPER,
    fold,
    is_greek_char,
    is_greek_upper,
    strip_accents,
)
from .ocr import normalize_ocr, normalize_whitespace

__all__ = [
    "GREEK_LETTERS",
    "GREEK_LOWER",
    "GREEK_UPPER",
    "fold",
    "is_greek_char",
    "is_greek_upper",
    "strip_accents",
    "normalize_ocr",
    "normalize_whitespace",
]
