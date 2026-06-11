"""Configuration for the anonymization engine.

A single ``AnonymizerConfig`` object controls which recognizers run, how
detected entities are replaced, and the confidence threshold below which
detections are discarded. Keeping all knobs in one dataclass makes the tool
easy to drive from the library, the CLI (flags) and the REST API (JSON body)
in a consistent way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .types import EntityType


class Strategy(str, Enum):
    """How a detected entity should be replaced in the output text.

    - REDACT: replace with a typed placeholder, e.g. ``[EMAIL]``.
    - TAG: replace with a typed, indexed placeholder, e.g. ``[EMAIL_1]`` so the
      same entity keeps a stable label (useful for downstream pipelines).
    - MASK: replace every character with a mask char, e.g. ``********``.
    - HASH: replace with a short deterministic hash of the value, allowing
      consistent pseudonymization without revealing the original.
    - REMOVE: drop the entity text entirely.
    """

    REDACT = "redact"
    TAG = "tag"
    MASK = "mask"
    HASH = "hash"
    REMOVE = "remove"


# Sensible default confidence floors per entity type. Regex-based entities are
# reliable, so they sit high; heuristic person detection is noisier.
DEFAULT_THRESHOLDS: Dict[EntityType, float] = {
    EntityType.EMAIL: 0.5,
    EntityType.PHONE: 0.5,
    EntityType.PERSON: 0.4,
}


@dataclass
class AnonymizerConfig:
    """Tunable settings for an :class:`~glossanon.engine.Anonymizer`.

    Attributes:
        entities: Which entity types to detect. Defaults to the standalone
            trio: email, phone, person.
        strategy: Default replacement strategy applied to all entities.
        per_entity_strategy: Optional overrides, e.g. hash emails but redact
            names.
        score_threshold: Global minimum confidence; entities scoring lower are
            dropped.
        per_entity_threshold: Optional per-type minimum confidence overrides.
        mask_char: Character used by the MASK strategy.
        hash_length: Number of hex chars kept for the HASH strategy.
        hash_salt: Salt mixed into HASH so pseudonyms differ across datasets.
        normalize_ocr: Run the OCR/text normalization pass before detection.
        use_ml: Enable the optional spaCy/Presidio backend if installed.
        ml_model: Name of the spaCy model to load when ``use_ml`` is on.
        markdown_aware: Skip fenced code blocks / inline code when anonymizing
            markdown produced by a PDF->md pipeline.
        keep_original: Retain the original text on the result object.
    """

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
        """Build a config from a plain dict (CLI/JSON friendly).

        Unknown keys are ignored so callers can pass through extra metadata
        without breaking. Enum-valued fields accept their string form.
        """
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
