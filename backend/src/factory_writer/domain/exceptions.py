class FactoryWriterError(Exception):
    """Erreur métier/infra contrôlée, exploitable par l'API et Temporal."""

    def __init__(
        self,
        message: str,
        code: str,
        *,
        status_code: int = 500,
        retryable: bool = False,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class ConfigurationError(FactoryWriterError):
    def __init__(self, message: str, *, code: str = "CONFIGURATION_ERROR") -> None:
        super().__init__(message, code, status_code=500, retryable=False)


class InvalidStyleGuideSourceIdError(FactoryWriterError):
    def __init__(self, raw_value: str):
        super().__init__(
            message=f"source_id invalide: {raw_value}",
            code="INVALID_STYLE_GUIDE_SOURCE_ID",
            status_code=400,
            retryable=False,
        )


class StyleGuideSourceNotFoundError(FactoryWriterError):
    def __init__(self, source_id: str):
        super().__init__(
            message=f"Source de guide de style introuvable: {source_id}",
            code="STYLE_GUIDE_SOURCE_NOT_FOUND",
            status_code=404,
            retryable=False,
        )


class InvalidGcsUriError(FactoryWriterError):
    def __init__(self, uri: str):
        super().__init__(
            message=f"URI GCS invalide: {uri}",
            code="INVALID_GCS_URI",
            status_code=400,
            retryable=False,
        )


class StyleGuideObjectNotFoundError(FactoryWriterError):
    def __init__(self, uri: str):
        super().__init__(
            message=f"Objet GCS introuvable ou métadonnées incomplètes: {uri}",
            code="STYLE_GUIDE_OBJECT_NOT_FOUND",
            status_code=404,
            retryable=False,
        )


class WorkflowStartError(FactoryWriterError):
    def __init__(self, details: str):
        super().__init__(
            message=f"Impossible de démarrer le workflow Temporal: {details}",
            code="WORKFLOW_START_ERROR",
            status_code=503,
            retryable=True,
        )


class DocumentAIOutputMissingError(FactoryWriterError):
    def __init__(self, output_uri: str):
        super().__init__(
            message=f"Document AI n'a produit aucun JSON exploitable sous {output_uri}",
            code="DOCUMENT_AI_OUTPUT_MISSING",
            status_code=422,
            retryable=False,
        )


class StyleGuideDocumentAIResourceNotFoundError(FactoryWriterError):
    def __init__(self, details: str):
        super().__init__(
            message=f"Ressource GCP introuvable pendant l'appel Document AI: {details}",
            code="DOCUMENT_AI_RESOURCE_NOT_FOUND",
            status_code=404,
            retryable=False,
        )


class StyleGuideDocumentAITransientError(FactoryWriterError):
    def __init__(self, details: str):
        super().__init__(
            message=f"Erreur GCP transitoire pendant l'appel Document AI: {details}",
            code="DOCUMENT_AI_TRANSIENT_ERROR",
            status_code=503,
            retryable=True,
        )


class StyleGuideDocumentAIProcessingError(FactoryWriterError):
    def __init__(self, details: str):
        super().__init__(
            message=f"Document AI a échoué pendant le traitement: {details}",
            code="DOCUMENT_AI_PROCESSING_FAILED",
            status_code=422,
            retryable=False,
        )
