from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class GCPSettings(BaseModel):
    project_id: str = "factory-writer-poc-1776097019"
    location: str = "europe-west1"
    document_ai_location: str = "eu"
    document_ai_processor_id: str = "684ca2ae2323b47c"
    style_guide_bucket_name: str = "factory-writer-poc-1776097019-brand-styles"


class TemporalSettings(BaseModel):
    address: str = "localhost:7233"
    namespace: str = "default"
    api_key: str | None = None


class DatabaseSettings(BaseModel):
    url: str = ""


class Settings(BaseSettings):
    app_name: str = "Factory Writer API"
    version: str = "0.1.0"
    debug: bool = False
    gcp: GCPSettings = GCPSettings()
    temporal: TemporalSettings = TemporalSettings()
    db: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
