from pydantic import BaseModel, ConfigDict, Field


class StorageObjectData(BaseModel):
    """
    Modélisation SOTA 2026 de l'objet métier de Google Cloud Storage.
    Le payload de Google est vaste, mais nous n'extrayons que ce qui nous est vital (DDD).
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Nom ou chemin unique du fichier dans le bucket.")
    bucket: str = Field(description="Nom global du bucket GCS.")
    size: int | str | None = Field(default=None, description="Taille du fichier.")
    content_type: str | None = Field(
        alias="contentType", default=None, description="Type MIME (ex: application/pdf)."
    )
    # Les autres informations comme generation, metageneration, timeCreated sont volontairement ignorées.
