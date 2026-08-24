"""Replacement strategies: turning detected entities into output text.

A :class:`ReplacementBuilder` is created per document so that strategies needing
consistency (``TAG``, ``HASH``) assign a *stable* label to repeated values - the
same phone number always becomes the same ``[PHONE_3]`` / hash within a
document, which downstream pipelines can rely on.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict

from .config import AnonymizerConfig, Strategy
from .normalization.greek import fold
from .types import Entity, EntityType

# Must match PhoneRecognizer._validate: str.isdigit() accepts more than \D strips.
_NON_DIGITS = re.compile(r"\D")


def _value_key(entity: Entity) -> str:
    """A normalized identity key so equal values map to equal pseudonyms."""
    if entity.entity_type == EntityType.PHONE:
        return entity.metadata.get("national") or _NON_DIGITS.sub("", entity.text)
    if entity.entity_type == EntityType.EMAIL:
        return entity.text.strip().lower()
    if entity.entity_type == EntityType.PERSON:
        return fold(entity.text)
    return entity.text.strip()


class ReplacementBuilder:
    """Produces the replacement string for each entity given a strategy."""

    def __init__(self, config: AnonymizerConfig) -> None:
        self.config = config
        # Per-type running counter for TAG, plus value->id memo for stability.
        self._counters: Dict[EntityType, int] = {}
        self._ids: Dict[tuple, int] = {}

    def _stable_id(self, entity: Entity) -> int:
        key = (entity.entity_type, _value_key(entity))
        if key not in self._ids:
            nxt = self._counters.get(entity.entity_type, 0) + 1
            self._counters[entity.entity_type] = nxt
            self._ids[key] = nxt
        return self._ids[key]

    def _hash(self, entity: Entity) -> str:
        payload = f"{self.config.hash_salt}:{entity.entity_type.value}:{_value_key(entity)}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest[: self.config.hash_length]

    def replacement_for(self, entity: Entity) -> str:
        strategy = self.config.strategy_for(entity.entity_type)
        etype = entity.entity_type.value

        if strategy == Strategy.REDACT:
            return f"[{etype}]"
        if strategy == Strategy.TAG:
            return f"[{etype}_{self._stable_id(entity)}]"
        if strategy == Strategy.MASK:
            return self.config.mask_char * max(1, entity.length)
        if strategy == Strategy.HASH:
            return f"[{etype}_{self._hash(entity)}]"
        if strategy == Strategy.REMOVE:
            return ""
        return f"[{etype}]"  # defensive default
