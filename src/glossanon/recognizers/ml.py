"""Optional ML backend for stronger name/organization detection.

This recognizer is **never imported by default**. It is only constructed when
``AnonymizerConfig.use_ml`` is true, and it imports its heavy dependencies
lazily so the core tool stays dependency-free.

Two backends are supported, tried in order:

1. **Microsoft Presidio** (``presidio-analyzer``) - if installed, used for
   multilingual PII analysis.
2. **spaCy** (``spacy`` + a model such as ``xx_ent_wiki_sm``) - used directly as
   a fallback for named-entity recognition.

If neither is available, constructing the recognizer raises a clear, actionable
error telling the user what to install.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..types import Entity, EntityType
from .base import Recognizer

# spaCy entity labels -> our entity types.
_SPACY_LABEL_MAP = {
    "PER": EntityType.PERSON,
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORG,
    "LOC": EntityType.LOCATION,
    "GPE": EntityType.LOCATION,
}

_PRESIDIO_LABEL_MAP = {
    "PERSON": EntityType.PERSON,
    "ORGANIZATION": EntityType.ORG,
    "LOCATION": EntityType.LOCATION,
    "EMAIL_ADDRESS": EntityType.EMAIL,
    "PHONE_NUMBER": EntityType.PHONE,
}


# Loaded backends are expensive and stateless: share one per (model, language).
_BACKEND_CACHE: Dict[Tuple[str, str], Tuple[str, Any]] = {}


class MlRecognizer(Recognizer):
    name = "ml"

    # The engine skips by declared type, so list what each backend really emits.
    _PRESIDIO_ENTITIES = (
        EntityType.PERSON,
        EntityType.ORG,
        EntityType.LOCATION,
        EntityType.EMAIL,
        EntityType.PHONE,
    )
    _SPACY_ENTITIES = (EntityType.PERSON, EntityType.ORG, EntityType.LOCATION)

    # Widest set; narrowed to the backend actually chosen in __init__.
    supported_entities = _PRESIDIO_ENTITIES

    def __init__(self, model: str = "xx_ent_wiki_sm", language: str = "el") -> None:
        self._backend: Optional[str] = None
        self._engine: Any = None
        self._language = language
        #: Why Presidio was rejected, if it was.
        self.presidio_error: Optional[str] = None

        cached = _BACKEND_CACHE.get((model, language))
        if cached is not None:
            self._backend, self._engine = cached
            self.supported_entities = (
                self._PRESIDIO_ENTITIES
                if self._backend == "presidio"
                else self._SPACY_ENTITIES
            )
            return

        # Try Presidio first.
        try:  # pragma: no cover - depends on optional install
            from presidio_analyzer import AnalyzerEngine  # type: ignore

            engine = AnalyzerEngine()
            # A default engine is English-only: check here, not at detection time.
            supported = tuple(getattr(engine, "supported_languages", ()) or ())
            if supported and language not in supported:
                raise RuntimeError(
                    f"the installed Presidio analyzer supports {list(supported)}, "
                    f"not {language!r}"
                )
            self._engine = engine
            self._backend = "presidio"
            self.supported_entities = self._PRESIDIO_ENTITIES
            _BACKEND_CACHE[(model, language)] = (self._backend, self._engine)
            return
        except Exception as exc:
            self.presidio_error = f"{type(exc).__name__}: {exc}"

        # Fall back to spaCy.
        try:  # pragma: no cover - depends on optional install
            import spacy  # type: ignore

            self._engine = spacy.load(model)
            self._backend = "spacy"
            self.supported_entities = self._SPACY_ENTITIES
            _BACKEND_CACHE[(model, language)] = (self._backend, self._engine)
            return
        except Exception as exc:
            detail = f"spaCy: {exc}"
            if self.presidio_error:
                detail += f"; Presidio: {self.presidio_error}"
            raise RuntimeError(
                "The ML backend requires either 'presidio-analyzer' (with an NLP "
                f"engine for language {language!r}) or 'spacy' with a model. "
                "Install with:\n"
                "  pip install \"glossanon[ml]\"\n"
                f"  python -m spacy download {model}\n"
                f"(underlying errors: {detail})"
            ) from exc

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        if self._backend == "presidio":
            return self._analyze_presidio(text)
        return self._analyze_spacy(text)

    def _analyze_presidio(self, text: str) -> List[Entity]:  # pragma: no cover
        results = self._engine.analyze(text=text, language=self._language)
        out: List[Entity] = []
        for r in results:
            etype = _PRESIDIO_LABEL_MAP.get(r.entity_type)
            if etype is None:
                continue
            out.append(
                Entity(
                    entity_type=etype,
                    start=r.start,
                    end=r.end,
                    text=text[r.start:r.end],
                    score=float(r.score),
                    recognizer=f"{self.name}:presidio",
                )
            )
        return out

    def _analyze_spacy(self, text: str) -> List[Entity]:  # pragma: no cover
        doc = self._engine(text)
        out: List[Entity] = []
        for ent in doc.ents:
            etype = _SPACY_LABEL_MAP.get(ent.label_)
            if etype is None:
                continue
            out.append(
                Entity(
                    entity_type=etype,
                    start=ent.start_char,
                    end=ent.end_char,
                    text=ent.text,
                    score=0.85,
                    recognizer=f"{self.name}:spacy",
                )
            )
        return out
