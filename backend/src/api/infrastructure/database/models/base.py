import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# cette petite classe vide contient en elle l'intégralité du code et des relations de ton projet !
class Base(DeclarativeBase):
    """
    Root base declarative class dictating SOTA 2026 configuration for Base models
    """

    pass  # "La classe est vide, je n'ai rien de plus à ajouter, circulez".


class BaseModel(Base):
    """
    Abstract Base Class with id, created_at, updated_at out of the box
    """

    # NE VA SURTOUT PAS créer de table physique nommée base_model dans la base de données
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # lambda = default: () => datetime.now(UTC), c'est une fonction lamdba
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
