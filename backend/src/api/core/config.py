from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'application Factory Writer.
    Gérée via pydantic-settings pour une validation stricte.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # FastAPI
    APP_NAME: str = Field(default="Factory Writer - Style Guide API")
    VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    # GCP
    GCP_PROJECT_ID: str = Field(default="factory-writer-poc-1776097019")
    GCP_LOCATION: str = Field(default="europe-west1")
    GCP_DOCUMENT_AI_LOCATION: str = Field(default="eu")
    GCP_DOCUMENT_AI_PROCESSOR_ID: str = Field(default="684ca2ae2323b47c")
    GCP_STYLE_GUIDE_BUCKET_NAME: str = Field(default="factory-writer-poc-1776097019-brand-styles")

    # DB SOTA 2026: psycopg async natif (Injectée par GCP Secret Manager)
    DATABASE_URL: str = Field(
        default="",
        description="URL de connexion à Postgres, injectée dynamiquement par le Secret Manager",
    )

    # Temporal
    TEMPORAL_HOST: str = Field(default="localhost:7233")


settings = Settings()
