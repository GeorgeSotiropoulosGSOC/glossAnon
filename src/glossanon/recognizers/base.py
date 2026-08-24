"""The recognizer interface.

A recognizer takes the original text plus a length-preserving normalized view
and returns a list of detected entities. Keeping the contract this small makes
recognizers trivial to test in isolation and easy to add or remove.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence

from ..normalization.greek import fold
from ..types import Entity, EntityType


class Recognizer(ABC):
    """Base class for all entity recognizers.

    Subclasses set :attr:`name` and :attr:`supported_entities`, and implement
    :meth:`analyze`. Detection may run against either the original ``text`` or
    the ``normalized`` view; because normalization is length-preserving, any
    offset is valid in both. Returned entities should always carry the
    *original* substring in :attr:`Entity.text`.
    """

    #: Human-readable recognizer name, recorded on every entity it produces.
    name: str = "recognizer"
    #: Entity types this recognizer can emit.
    supported_entities: Sequence[EntityType] = ()

    @abstractmethod
    def analyze(self, text: str, normalized: str) -> List[Entity]:
        """Return entities found in ``text``.

        Args:
            text: The original input text. Use this for the entity's ``text``.
            normalized: A length-preserving, OCR-cleaned view of ``text``.
                Offsets discovered here map directly back onto ``text``.
        """
        raise NotImplementedError

    def supports(self, entity_type: EntityType) -> bool:
        return entity_type in self.supported_entities


def label_precedes(text: str, start: int, labels: Sequence[str], window: int = 16) -> bool:
    """True if one of ``labels`` appears just before ``start``.

    Used by the identifier recognizers: a bare number that passes a checksum is
    suggestive, but an explicit ``ΑΦΜ:`` / ``ΑΜΚΑ:`` label alongside it is
    conclusive. Comparison ignores case, accents, dots and spaces.
    """
    prefix = fold(text[max(0, start - window):start])
    squashed = prefix.replace(".", "").replace(" ", "").replace(":", "")
    return any(squashed.endswith(fold(lab)) for lab in labels)
