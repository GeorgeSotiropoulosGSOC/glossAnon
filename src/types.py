from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    """Categories of personal data the tool can detect.

    Inherits from ``str`` so values serialize cleanly to JSON and can be
    compared directly to plain strings (``entity.entity_type == "EMAIL"``).
    The initial standalone release focuses on EMAIL, PHONE and PERSON, but the
    enum is open for extension (AFM, AMKA, IBAN, ORG, LOCATION ...).
    """

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PERSON = "PERSON"

    ORG = "ORG"
    LOCATION = "LOCATION"
    AFM = "AFM"          
    AMKA = "AMKA"        
    IBAN = "IBAN"
    URL = "URL"
    DATE = "DATE"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


@dataclass(frozen=True)
class Entity:
    """A single detected piece of personal data within a text.

    Attributes:
        entity_type: The category of the entity.
        start: Inclusive character offset where the entity begins.
        end: Exclusive character offset where the entity ends.
        text: The exact substring that was matched (``source[start:end]``).
        score: Confidence in ``[0.0, 1.0]``. Regex matches are typically high
            confidence; heuristic name matches are lower.
        recognizer: Name of the recognizer that produced this entity. Useful
            for debugging, auditing and tuning.
        metadata: Free-form extra information (e.g. the normalized value).
    """

    entity_type: EntityType
    start: int
    end: int
    text: str
    score: float = 1.0
    recognizer: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: "Entity") -> bool:
        """True if this entity shares any character span with ``other``."""
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["entity_type"] = self.entity_type.value
        return data


@dataclass
class AnonymizationResult:

    text: str
    entities: List[Entity] = field(default_factory=list)
    original_text: Optional[str] = None

    @property
    def count(self) -> int:
        return len(self.entities)

    def counts_by_type(self) -> Dict[str, int]:
        """How many entities of each type were found (handy for reports)."""
        out: Dict[str, int] = {}
        for ent in self.entities:
            key = ent.entity_type.value
            out[key] = out.get(key, 0) + 1
        return out

    def to_dict(self, include_original: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "text": self.text,
            "entities": [e.to_dict() for e in self.entities],
            "counts": self.counts_by_type(),
        }
        if include_original and self.original_text is not None:
            data["original_text"] = self.original_text
        return data
