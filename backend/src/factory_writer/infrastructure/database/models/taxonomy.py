from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from factory_writer.infrastructure.database.models.base import BaseModel


class TaxonomieProduit(BaseModel):
    __tablename__ = "taxonomie_produit"

    famille_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    libelle_fr: Mapped[str] = mapped_column(String)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True
    )

    parent = relationship(
        "TaxonomieProduit",
        remote_side="TaxonomieProduit.id",
        back_populates="children",
    )
    children = relationship("TaxonomieProduit", back_populates="parent")
    products = relationship("Product", back_populates="taxonomie_produit")
    style_rules = relationship("StyleRule", back_populates="taxonomie_produit")
