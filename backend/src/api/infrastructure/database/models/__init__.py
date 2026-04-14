# Exposer les modèles pour Alembic
from api.infrastructure.database.models.base import Base, BaseModel
from api.infrastructure.database.models.style_guide import (
    FragmentStyle,
    PackStyle,
    RegleStyle,
    SourceGuideStyle,
    TaxonomieProduit,
)

__all__ = [
    "Base",
    "BaseModel",
    "SourceGuideStyle",
    "FragmentStyle",
    "PackStyle",
    "TaxonomieProduit",
    "RegleStyle",
]
