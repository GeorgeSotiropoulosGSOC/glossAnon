"""Greek social security number (ΑΜΚΑ) recognizer.

An ΑΜΚΑ is 11 digits: ``DDMMYY`` of the holder's birth date, then four serial
digits, then a Luhn check digit over the whole number. Requiring a plausible
date prefix *and* a passing Luhn check makes a false positive on an arbitrary
11-digit run unlikely.
"""

from __future__ import annotations

import re
from typing import List

from ..types import Entity, EntityType
from .base import Recognizer, label_precedes

_CANDIDATE_RE = re.compile(r"(?<![\w])\d{11}(?![\w])")

_LABELS = ("αμκα", "amka")


def luhn_ok(digits: str) -> bool:
    """Standard Luhn checksum over a digit string, check digit included."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def is_valid(digits: str) -> bool:
    """True if ``digits`` is 11 digits, opens with a plausible DDMM, and passes Luhn."""
    if len(digits) != 11 or not digits.isdigit():
        return False
    day, month = int(digits[0:2]), int(digits[2:4])
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return False
    return luhn_ok(digits)


class AmkaRecognizer(Recognizer):
    name = "amka"
    supported_entities = (EntityType.AMKA,)

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        found: List[Entity] = []
        for m in _CANDIDATE_RE.finditer(normalized):
            if not is_valid(m.group(0)):
                continue
            labelled = label_precedes(normalized, m.start(), _LABELS)
            found.append(
                Entity(
                    entity_type=EntityType.AMKA,
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                    score=0.95 if labelled else 0.8,
                    recognizer=self.name,
                    metadata={"labelled": labelled, "birth_ddmmyy": m.group(0)[:6]},
                )
            )
        return found
