"""FastAPI application exposing the anonymizer over HTTP.

Endpoints:

* ``GET  /health``           - liveness probe
* ``GET  /info``             - supported entity types and strategies
* ``POST /anonymize``        - anonymize a single text
* ``POST /anonymize/batch``  - anonymize many texts at once

Run it with::

    uvicorn glossanon.api.app:app --reload
    # or
    glossanon-serve
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "The REST API requires FastAPI. Install with: pip install \"glossanon[api]\""
    ) from exc

from .. import __version__
from ..config import AnonymizerConfig, Strategy
from ..engine import Anonymizer
from ..types import EntityType


# -- request/response models --------------------------------------------------

class AnonymizeRequest(BaseModel):
    text: str = Field(..., description="The text to anonymize.")
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional engine configuration (strategy, entities, ...).",
    )
    include_entities: bool = Field(
        default=True, description="Return the list of detected entities."
    )


class BatchRequest(BaseModel):
    texts: List[str]
    config: Optional[Dict[str, Any]] = None
    include_entities: bool = True


# -- engine caching -----------------------------------------------------------

_CACHE: Dict[str, Anonymizer] = {}
# Bounded: the key is the whole config, which a client can vary per request.
_CACHE_MAX_ENTRIES = 32


def _get_engine(config: Optional[Dict[str, Any]]) -> Anonymizer:
    """Return a cached engine for a given config dict (cheap to reuse)."""
    key = json.dumps(config or {}, sort_keys=True, ensure_ascii=False)
    engine = _CACHE.get(key)
    if engine is None:
        try:
            cfg = AnonymizerConfig.from_dict(config)
            engine = Anonymizer(cfg)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"invalid config: {exc}") from exc
        except RuntimeError as exc:
            # A missing backend is a server problem, not a malformed request.
            raise HTTPException(
                status_code=503, detail=f"backend unavailable: {exc}"
            ) from exc
        if len(_CACHE) >= _CACHE_MAX_ENTRIES:
            _CACHE.clear()
        _CACHE[key] = engine
    return engine


def _result_payload(result, include_entities: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "text": result.text,
        "counts": result.counts_by_type(),
    }
    if include_entities:
        payload["entities"] = [e.to_dict() for e in result.entities]
    return payload


# -- app factory --------------------------------------------------------------

def create_app() -> "FastAPI":
    app = FastAPI(
        title="glossanon",
        version=__version__,
        description="Lightweight ML-assisted anonymization for Greek text.",
    )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/info")
    def info() -> Dict[str, Any]:
        return {
            "version": __version__,
            "entities": [e.value for e in EntityType],
            "default_entities": [e.value for e in AnonymizerConfig().entities],
            "strategies": [s.value for s in Strategy],
        }

    @app.post("/anonymize")
    def anonymize(req: AnonymizeRequest) -> Dict[str, Any]:
        engine = _get_engine(req.config)
        result = engine.anonymize(req.text)
        return _result_payload(result, req.include_entities)

    @app.post("/anonymize/batch")
    def anonymize_batch(req: BatchRequest) -> Dict[str, Any]:
        engine = _get_engine(req.config)
        results = engine.anonymize_batch(req.texts)
        return {
            "results": [_result_payload(r, req.include_entities) for r in results]
        }

    return app


# Module-level app for `uvicorn glossanon.api.app:app`.
app = create_app()
