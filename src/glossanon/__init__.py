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
