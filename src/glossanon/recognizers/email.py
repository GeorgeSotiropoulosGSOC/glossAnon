"""Email address recognizer.

A pragmatic, OCR-tolerant email matcher. It catches standard addresses and a
couple of light obfuscations commonly seen in public documents
(``name [at] domain.gr``, ``name(at)domain.gr``).
"""

from __future__ import annotations

import re
from typing import List

from ..types import Entity, EntityType
from .base import Recognizer

# Deliberately not full RFC 5322: enormous, and matches what documents never hold.
_EMAIL_RE = re.compile(
    r"(?<![\w.+-])"
    r"[A-Za-z0-9._%+\-]+"          # local part
    r"@"
    r"[A-Za-z0-9.\-]+"            # domain
    r"\.[A-Za-z]{2,24}"          # TLD
    r"(?![\w-])"
)

# Lightly obfuscated forms: " at " / "(at)" / "[at]" and " dot ".
_OBFUSCATED_RE = re.compile(
    r"(?<![\w.+-])"
    r"[A-Za-z0-9._%+\-]+"
    r"\s*[\(\[]?\s*(?:at|στο|παπάκι)\s*[\)\]]?\s*"
    r"[A-Za-z0-9.\-]+"
    r"\s*[\(\[]?\s*(?:dot|τελεία)\s*[\)\]]?\s*"
    r"[A-Za-z]{2,24}",
    re.IGNORECASE,
)


class EmailRecognizer(Recognizer):
    name = "email"
    supported_entities = (EntityType.EMAIL,)

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        # Match normalized (OCR look-alikes repaired); offsets still index text.
        found: List[Entity] = []
        seen_spans: set[tuple[int, int]] = set()

        for m in _EMAIL_RE.finditer(normalized):
            seen_spans.add((m.start(), m.end()))
            found.append(
                Entity(
                    entity_type=EntityType.EMAIL,
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                    score=0.99,
                    recognizer=self.name,
                )
            )

        for m in _OBFUSCATED_RE.finditer(normalized):
            # Skip if already covered by the strict matcher.
            if any(s <= m.start() and m.end() <= e for s, e in seen_spans):
                continue
            found.append(
                Entity(
                    entity_type=EntityType.EMAIL,
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                    score=0.7,
                    recognizer=self.name,
                    metadata={"obfuscated": True},
                )
            )

        return found
