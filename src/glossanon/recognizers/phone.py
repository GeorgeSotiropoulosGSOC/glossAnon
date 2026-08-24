"""Greek phone number recognizer.

Strategy: scan for loosely-grouped digit sequences (a *candidate*), then strip
separators and validate against Greek numbering rules. This two-step approach is
robust to the varied formatting found in real documents
(``2101234567``, ``210 123 4567``, ``+30 698 123 4567``, ``(2310) 123456`` ...)
while staying precise.

Greek numbering facts used for validation:

* National numbers are **10 digits**.
* Geographic (landline) numbers start with **2**.
* Mobile numbers start with **69**.
* Common service ranges start with 800/801/807/896/901/909/700.
* International form is ``+30`` / ``0030`` followed by the 10 national digits.

The fixed 10-digit rule conveniently excludes 9-digit ΑΦΜ (tax id) and 11-digit
ΑΜΚΑ numbers, reducing false positives.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from ..types import Entity, EntityType
from .base import Recognizer

# Digit runs joined by single separators; starts and ends on a digit.
_CANDIDATE_RE = re.compile(
    r"(?<![\w])"
    r"\+?\d(?:[\d]|[ .\-/](?=\d)){7,16}\d"
    r"(?![\w])"
)

_SERVICE_PREFIXES = {"800", "801", "807", "896", "901", "909", "700", "806"}


def _validate(raw: str) -> Optional[Tuple[str, float]]:
    """Validate a raw candidate string. Returns (national_digits, score) or None."""
    digits = re.sub(r"\D", "", raw)
    had_cc = False

    if digits.startswith("0030"):
        digits = digits[4:]
        had_cc = True
    elif digits.startswith("30") and len(digits) == 12:
        digits = digits[2:]
        had_cc = True

    if len(digits) != 10:
        return None

    # Formatting cues raise confidence; a bare 10-digit run is ambiguous.
    formatted = had_cc or bool(re.search(r"[ .\-/()]|\+", raw))

    if digits.startswith("69"):
        return digits, 0.95 if formatted else 0.75  # mobile
    if digits.startswith("2"):
        return digits, 0.9 if formatted else 0.7    # geographic / landline
    if digits[:3] in _SERVICE_PREFIXES:
        return digits, 0.9
    return None


class PhoneRecognizer(Recognizer):
    name = "phone"
    supported_entities = (EntityType.PHONE,)

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        # Scan normalized (exotic spaces repaired); offsets still index text.
        found: List[Entity] = []
        for m in _CANDIDATE_RE.finditer(normalized):
            result = _validate(m.group(0))
            if result is None:
                continue
            national, score = result
            found.append(
                Entity(
                    entity_type=EntityType.PHONE,
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                    score=score,
                    recognizer=self.name,
                    metadata={"national": national},
                )
            )
        return found
