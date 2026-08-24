"""glossanon - lightweight, ML-assisted anonymization for Greek text.

A standalone tool that detects and replaces personal data (emails, phone
numbers and names) in Greek documents. It is designed to run anywhere with a
zero-dependency core, and to slot cleanly into a document pipeline
(PDF -> markdown -> clear text -> anonymization).

Quick start::

    from glossanon import Anonymizer

    result = Anonymizer().anonymize("Επικοινωνία: Γιώργος Παπαδόπουλος, 6981234567")
    print(result.text)
    # -> "Επικοινωνία: [PERSON], [PHONE]"

The heavy pieces (FastAPI server, spaCy/Presidio backend) are optional extras
and are imported lazily, so ``import glossanon`` stays fast and dependency-free.
"""

from .config import AnonymizerConfig, Strategy
from .engine import Anonymizer
from .types import AnonymizationResult, Entity, EntityType

__version__ = "0.1.0"

__all__ = [
    "Anonymizer",
    "AnonymizerConfig",
    "Strategy",
    "AnonymizationResult",
    "Entity",
    "EntityType",
    "__version__",
]
