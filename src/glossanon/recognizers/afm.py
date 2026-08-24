"""Greek tax identification number (ΑΦΜ) recognizer.

An ΑΦΜ is 9 digits with a check digit: the first 8 digits are weighted by
descending powers of two, summed, then reduced ``mod 11 mod 10`` to give the
ninth. That rejects roughly 9 in 10 random 9-digit runs, so the checksum alone
is decent evidence; an explicit ``ΑΦΜ:`` label alongside it makes it certain.

The 9-digit length keeps ΑΦΜ distinct from 10-digit phone numbers and 11-digit
ΑΜΚΑ, so the three identifier recognizers cannot claim the same span.
"""

from __future__ import annotations

import re
from typing import List

from ..types import Entity, EntityType
from .base import Recognizer, label_precedes

_CANDIDATE_RE = re.compile(r"(?<![\w])\d{9}(?![\w])")

_LABELS = ("αφμ", "afm", "vat")


def check_digit(digits: str) -> int:
    """The expected 9th digit for the first 8 of an ΑΦΜ."""
    return sum(int(d) << (8 - i) for i, d in enumerate(digits[:8])) % 11 % 10


def is_valid(digits: str) -> bool:
    """True if ``digits`` is a 9-digit string with a correct ΑΦΜ check digit."""
    if len(digits) != 9 or not digits.isdigit():
        return False
    if digits == "000000000":
        return False
    return check_digit(digits) == int(digits[8])


class AfmRecognizer(Recognizer):
    name = "afm"
    supported_entities = (EntityType.AFM,)

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        found: List[Entity] = []
        for m in _CANDIDATE_RE.finditer(normalized):
            if not is_valid(m.group(0)):
                continue
            labelled = label_precedes(normalized, m.start(), _LABELS)
            found.append(
                Entity(
                    entity_type=EntityType.AFM,
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                    score=0.95 if labelled else 0.7,
                    recognizer=self.name,
                    metadata={"labelled": labelled},
                )
            )
        return found
