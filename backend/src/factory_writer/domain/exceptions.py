class BaseDomainException(Exception):
    """Base class for all domain exceptions in Factory Writer."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(self.message)


class WrongBucketError(BaseDomainException):
    def __init__(self, bucket_name: str, expected_bucket: str):
        super().__init__(
            message=f"Le bucket est invalide. Actuel: {bucket_name}, Attendu: {expected_bucket}",
            code="WRONG_BUCKET",
        )


class NotAPdfError(BaseDomainException):
    def __init__(self, file_name: str):
        super().__init__(
            message=f"Le fichier '{file_name}' n'est pas un fichier PDF valide.",
            code="NOT_A_PDF",
        )


class StyleGuideAlreadyExistsError(BaseDomainException):
    def __init__(self, uri: str):
        super().__init__(
            message=f"Le document avec l'URI '{uri}' a déjà été ingéré.", code="ALREADY_EXISTS"
        )
