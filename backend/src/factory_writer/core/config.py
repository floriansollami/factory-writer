from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class GCPSettings(BaseModel):
    project_id: str = ""
    location: str = "global"
    document_ai_location: str = "eu"
    document_ai_processor_id: str = ""
    document_ai_processor_version: str | None = None
    document_ai_classifier_processor_id: str = ""
    document_ai_classifier_processor_version: str | None = None
    document_ai_ocr_processor_id: str = ""
    document_ai_ocr_processor_version: str | None = None
    document_ai_extractor_processor_id: str = ""
    document_ai_extractor_processor_version: str | None = None
    style_guide_bucket_name: str = ""
    technical_dossier_bucket_name: str = ""
    storage_emulator_host: str = ""


class TemporalSettings(BaseModel):
    address: str = "localhost:7233"
    namespace: str = "default"
    api_key: str | None = None
    worker_role: str = "style-guide-ingestion"
    deployment_name: str = "factory-writer"
    build_id: str | None = None


class DatabaseSettings(BaseModel):
    url: str = ""


class LLMSettings(BaseModel):
    style_guide_timeout_seconds: float = 180.0
    style_guide_prompt_name: str = "style_guide_extract_rules"
    style_guide_prompt_version: str = "v1"


class TechnicalDossierSettings(BaseModel):
    sla_budget_seconds: float = 60.0
    low_confidence_threshold: float = 0.75
    max_pdf_bytes: int = 25 * 1024 * 1024


class Settings(BaseSettings):
    app_name: str = "Factory Writer API"
    version: str = "0.1.0"
    debug: bool = False
    gcp: GCPSettings = GCPSettings()
    temporal: TemporalSettings = TemporalSettings()
    db: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    technical_dossier: TechnicalDossierSettings = TechnicalDossierSettings()

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
