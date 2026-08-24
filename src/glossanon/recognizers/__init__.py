"""Pluggable entity recognizers.

Each recognizer is a small, self-contained unit that scans text and returns
:class:`~glossanon.types.Entity` objects for one (or a few) entity types. They
all implement the :class:`~glossanon.recognizers.base.Recognizer` interface, so
the engine can mix and match them, and new ones can be added without touching
the engine.
"""

from .base import Recognizer, label_precedes
from .afm import AfmRecognizer
from .amka import AmkaRecognizer
from .email import EmailRecognizer
from .iban import IbanRecognizer
from .phone import PhoneRecognizer
from .names import NameRecognizer

# Default recognizer set for the standalone tool.
DEFAULT_RECOGNIZERS = [
    EmailRecognizer,
    PhoneRecognizer,
    NameRecognizer,
    AfmRecognizer,
    AmkaRecognizer,
    IbanRecognizer,
]

__all__ = [
    "Recognizer",
    "label_precedes",
    "AfmRecognizer",
    "AmkaRecognizer",
    "EmailRecognizer",
    "IbanRecognizer",
    "PhoneRecognizer",
    "NameRecognizer",
    "DEFAULT_RECOGNIZERS",
]
