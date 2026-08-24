"""The anonymization engine: orchestration from raw text to clean output.

Pipeline per document:

1. **Normalize** - optional length-preserving OCR repair (offsets stay valid).
2. **Detect** - run every enabled recognizer, collect candidate entities.
3. **Filter** - drop entities of disabled types or below their confidence
   threshold; in markdown mode, drop those inside code blocks.
4. **Resolve overlaps** - keep the most confident / longest non-overlapping set.
5. **Replace** - rewrite the original text at each kept span using the
   configured strategy.

The engine is the single public entry point used by the library, CLI and API.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from .anonymizers import ReplacementBuilder
from .config import AnonymizerConfig
from .normalization.ocr import normalize_ocr
from .recognizers import DEFAULT_RECOGNIZERS
from .recognizers.base import Recognizer
from .types import AnonymizationResult, Entity

# Fenced code blocks and inline code in markdown - protected in markdown mode.
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


class Anonymizer:
    """Detects and replaces personal data in Greek text.

    Args:
        config: Engine configuration. Defaults to :class:`AnonymizerConfig`.
        recognizers: Explicit recognizer instances. When omitted, the default
            set (email, phone, names) is built, plus the ML backend if
            ``config.use_ml`` is enabled.
    """

    def __init__(
        self,
        config: Optional[AnonymizerConfig] = None,
        recognizers: Optional[Sequence[Recognizer]] = None,
    ) -> None:
        self.config = config or AnonymizerConfig()
        if recognizers is not None:
            self.recognizers: List[Recognizer] = list(recognizers)
        else:
            self.recognizers = [cls() for cls in DEFAULT_RECOGNIZERS]
            if self.config.use_ml:
                from .recognizers.ml import MlRecognizer

                self.recognizers.append(MlRecognizer(model=self.config.ml_model))

    # -- detection -------------------------------------------------------

    def analyze(self, text: str) -> List[Entity]:
        """Return the final, de-overlapped set of detected entities."""
        normalized = normalize_ocr(text) if self.config.normalize_ocr else text

        candidates: List[Entity] = []
        for rec in self.recognizers:
            # Skip recognizers whose entities are all disabled.
            if rec.supported_entities and not any(
                self.config.is_enabled(e) for e in rec.supported_entities
            ):
                continue
            candidates.extend(rec.analyze(text, normalized))

        protected = self._protected_spans(text) if self.config.markdown_aware else []
        kept = self._filter(candidates, protected)
        resolved = self._resolve_overlaps(kept)
        resolved.sort(key=lambda e: e.start)
        return resolved

    def _protected_spans(self, text: str) -> List[Tuple[int, int]]:
        spans = [(m.start(), m.end()) for m in _FENCE_RE.finditer(text)]
        spans += [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(text)]
        return spans

    def _filter(
        self, entities: Iterable[Entity], protected: Sequence[Tuple[int, int]]
    ) -> List[Entity]:
        out: List[Entity] = []
        for e in entities:
            if not self.config.is_enabled(e.entity_type):
                continue
            if e.score < self.config.threshold_for(e.entity_type):
                continue
            if any(ps <= e.start and e.end <= pe for ps, pe in protected):
                continue
            out.append(e)
        return out

    @staticmethod
    def _resolve_overlaps(entities: List[Entity]) -> List[Entity]:
        """Greedily keep the strongest, longest, non-overlapping entities."""
        # Highest score first, then longest, then earliest for determinism.
        ordered = sorted(entities, key=lambda e: (-e.score, -e.length, e.start))
        chosen: List[Entity] = []
        for cand in ordered:
            if any(cand.overlaps(c) for c in chosen):
                continue
            chosen.append(cand)
        return chosen

    # -- anonymization ---------------------------------------------------

    def anonymize(self, text: str) -> AnonymizationResult:
        """Detect and replace entities, returning the anonymized text."""
        entities = self.analyze(text)
        builder = ReplacementBuilder(self.config)

        out_parts: List[str] = []
        cursor = 0
        for ent in entities:
            out_parts.append(text[cursor:ent.start])
            out_parts.append(builder.replacement_for(ent))
            cursor = ent.end
        out_parts.append(text[cursor:])

        return AnonymizationResult(
            text="".join(out_parts),
            entities=entities,
            original_text=text if self.config.keep_original else None,
        )

    def anonymize_batch(self, texts: Iterable[str]) -> List[AnonymizationResult]:
        """Anonymize many texts (e.g. a corpus of extracted documents)."""
        return [self.anonymize(t) for t in texts]


def anonymize(text: str, config: Optional[AnonymizerConfig] = None) -> AnonymizationResult:
    """Convenience one-shot helper: ``anonymize("...").text``."""
    return Anonymizer(config).anonymize(text)
