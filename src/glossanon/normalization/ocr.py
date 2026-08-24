"""Length-preserving OCR repair for scanned Greek text.

Scanned/OCR'd Greek documents frequently mix in Latin characters that *look*
identical to Greek ones (the classic ``A E H O P T X`` confusables), plus a
zoo of exotic whitespace and look-alike digits. Left untouched, these break
both dictionary lookups (a name with one Latin letter won't match) and regex
patterns.

The functions here repair the most common cases **without changing string
length**, so the cleaned text can be used purely as a detection "view" while
every character offset still lines up with the original document. The actual
anonymized output is always built by editing the original text at those
offsets - we never emit the normalized view to the user.
"""

from __future__ import annotations

import re

from .greek import GREEK_LETTERS, is_greek_char

# Latin -> Greek look-alikes. 1:1 entries only, so length is preserved.
_LATIN_TO_GREEK = {
    # uppercase
    "A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ", "H": "Η", "I": "Ι",
    "K": "Κ", "M": "Μ", "N": "Ν", "O": "Ο", "P": "Ρ", "T": "Τ",
    "Y": "Υ", "X": "Χ",
    # lowercase
    "a": "α", "e": "ε", "o": "ο", "v": "ν", "u": "υ", "p": "ρ",
    "x": "χ", "y": "γ", "k": "κ", "i": "ι", "t": "τ", "n": "η",
}

# Exact mirror: a missing reverse entry lets a stray Greek glyph survive.
_GREEK_TO_LATIN = {greek: latin for latin, greek in _LATIN_TO_GREEK.items()}

# Exotic whitespace -> plain space. Single chars, so length is preserved.
_WHITESPACE_LOOKALIKES = {
    "\u00a0": " ",  # no-break space
    "\u2007": " ",  # figure space
    "\u2009": " ",  # thin space
    "\u200a": " ",  # hair space
    "\u202f": " ",  # narrow no-break space
    "\ufeff": " ",  # zero-width no-break / BOM (rendered as space here)
    "\t": " ",
}

# An alphabetic run. Built from GREEK_LETTERS so it cannot drift from greek.py.
_TOKEN_RE = re.compile("[A-Za-z" + re.escape(GREEK_LETTERS) + "]+")


def normalize_whitespace(text: str) -> str:
    """Replace exotic whitespace with regular spaces (length-preserving)."""
    return text.translate(str.maketrans(_WHITESPACE_LOOKALIKES))


def _repair_token(token: str) -> str:
    """Repair a single alphabetic token toward its dominant alphabet.

    If a token already contains Greek letters and a minority of Latin
    look-alikes, the Latin ones are converted to Greek (the common OCR case for
    Greek words). If a token is dominated by Latin letters, stray Greek
    look-alikes are converted to Latin. Tokens that are cleanly one alphabet are
    returned unchanged.
    """
    greek = sum(1 for ch in token if is_greek_char(ch))
    latin = sum(1 for ch in token if ch.isascii() and ch.isalpha())
    if greek == 0 or latin == 0:
        return token  # already homogeneous - nothing to repair

    if greek >= latin:
        # Greek-dominant word with intruding Latin glyphs -> push to Greek.
        return "".join(_LATIN_TO_GREEK.get(ch, ch) for ch in token)
    # Latin-dominant token with intruding Greek glyphs -> push to Latin.
    return "".join(_GREEK_TO_LATIN.get(ch, ch) for ch in token)


def normalize_ocr(text: str) -> str:
    """Return a cleaned, length-preserving view of ``text`` for detection.

    Steps (each preserves character count):

    1. Normalize exotic whitespace to regular spaces.
    2. Repair mixed-alphabet tokens toward their dominant alphabet.

    The returned string has exactly ``len(text)`` characters, so offsets found
    in it are valid offsets into the original ``text``.
    """
    text = normalize_whitespace(text)
    out = _TOKEN_RE.sub(lambda m: _repair_token(m.group(0)), text)
    # Safety net: never let normalization change length (would desync offsets).
    if len(out) != len(text):  # pragma: no cover - defensive
        return text
    return out
