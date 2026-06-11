from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .types import EntityType


class Strategy(str, Enum):


    REDACT = "redact"
    TAG = "tag"
    MASK = "mask"
    HASH = "hash"
    REMOVE = "remove"


DEFAULT_THRESHOLDS: Dict[EntityType, float] = {
    EntityType.EMAIL: 0.5,
    EntityType.PHONE: 0.5,
    EntityType.PERSON: 0.4,
}


@dataclass
class AnonymizerConfig:

    entities: List[EntityType] = field(
        default_factory=lambda: [
            EntityType.EMAIL,
            EntityType.PHONE,
            EntityType.PERSON,
        ]
    )
    strategy: Strategy = Strategy.REDACT
    per_entity_strategy: Dict[EntityType, Strategy] = field(default_factory=dict)

    score_threshold: float = 0.4
    per_entity_threshold: Dict[EntityType, float] = field(
        default_factory=lambda: dict(DEFAULT_THRESHOLDS)
    )

    mask_char: str = "*"
    hash_length: int = 8
    hash_salt: str = "glossanon"

    normalize_ocr: bool = True
    use_ml: bool = False
    ml_model: str = "xx_ent_wiki_sm"

    markdown_aware: bool = False
    keep_original: bool = False

    def is_enabled(self, entity_type: EntityType) -> bool:
        return entity_type in self.entities

    def threshold_for(self, entity_type: EntityType) -> float:
        return self.per_entity_threshold.get(entity_type, self.score_threshold)

    def strategy_for(self, entity_type: EntityType) -> Strategy:
        return self.per_entity_strategy.get(entity_type, self.strategy)

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "AnonymizerConfig":
       
        data = dict(data or {})
        cfg = cls()
        if "entities" in data and data["entities"] is not None:
            cfg.entities = [EntityType(e) for e in data["entities"]]
        if data.get("strategy"):
            cfg.strategy = Strategy(data["strategy"])
        if data.get("per_entity_strategy"):
            cfg.per_entity_strategy = {
                EntityType(k): Strategy(v)
                for k, v in data["per_entity_strategy"].items()
            }
        for key in (
            "score_threshold",
            "mask_char",
            "hash_length",
            "hash_salt",
            "normalize_ocr",
            "use_ml",
            "ml_model",
            "markdown_aware",
            "keep_original",
        ):
            if key in data and data[key] is not None:
                setattr(cfg, key, data[key])
        if data.get("per_entity_threshold"):
            cfg.per_entity_threshold.update(
                {EntityType(k): float(v) for k, v in data["per_entity_threshold"].items()}
            )
        return cfg
