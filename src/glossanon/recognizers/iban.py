"""IBAN recognizer, tuned for Greek accounts.

Validation is the ISO 13616 mod-97 check: move the first four characters to the
end, map letters to numbers (A=10 ... Z=35), and the result must be 1 mod 97.
That is strong enough on its own that no context label is needed.

Greek IBANs are 27 characters and score highest; other valid countries are still
reported, slightly lower.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..types import Entity, EntityType
from .base import Recognizer

# Two letters, two check digits, then the account in optionally-spaced groups.
_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]{2}\d{2}(?:[ ]?[A-Za-z0-9]){11,30})(?![A-Za-z0-9])"
)

_COUNTRY_LENGTHS = {"GR": 27, "CY": 28, "DE": 22, "GB": 22, "FR": 27, "IT": 27, "NL": 18}


def compact(raw: str) -> str:
    return raw.replace(" ", "").upper()


def mod97_ok(value: str) -> bool:
    """ISO 13616 mod-97 check on an already-compacted IBAN."""
    if not (15 <= len(value) <= 34) or not value[:2].isalpha() or not value[2:4].isdigit():
        return False
    rearranged = value[4:] + value[:4]
    digits = []
    for ch in rearranged:
        if ch.isdigit():
            digits.append(ch)
        elif ch.isalpha():
            digits.append(str(ord(ch) - 55))
        else:
            return False
    return int("".join(digits)) % 97 == 1


def validate(raw: str) -> Optional[float]:
    """Return a confidence score for a candidate IBAN, or None if invalid."""
    value = compact(raw)
    expected = _COUNTRY_LENGTHS.get(value[:2])
    if expected is not None and len(value) != expected:
        return None
    if not mod97_ok(value):
        return None
    return 0.98 if value.startswith("GR") else 0.9


class IbanRecognizer(Recognizer):
    name = "iban"
    supported_entities = (EntityType.IBAN,)

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        found: List[Entity] = []
        for m in _CANDIDATE_RE.finditer(normalized):
            score = validate(m.group(1))
            if score is None:
                continue
            start, end = m.start(1), m.end(1)
            found.append(
                Entity(
                    entity_type=EntityType.IBAN,
                    start=start,
                    end=end,
                    text=text[start:end],
                    score=score,
                    recognizer=self.name,
                    metadata={"compact": compact(m.group(1))},
                )
            )
        return found
