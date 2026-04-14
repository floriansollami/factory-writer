from pydantic import BaseModel, Field


class StyleGuideIngestionInput(BaseModel):
    """
    Input structurel pour déclencher le Workflow d'ingestion d'un Style Guide.
    Garanti l'idempotence via source_id.
    """

    source_id: str = Field(..., description="UUID du SourceGuideStyle stocké en BDD")
    file_uri: str = Field(..., description="URI standardisé GCS vers le fichier PDF")


class StyleGuideIngestionOutput(BaseModel):
    """
    Output structurel retourné à la fin du Workflow en cas de succès nominal.
    """

    status: str = Field(..., description="Statut final (ex: 'success')")
    pack_id: str = Field(..., description="UUID du StylePack actif généré et approuvé")
