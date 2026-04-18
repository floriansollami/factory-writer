from dataclasses import dataclass


@dataclass(frozen=True)
class GcsUri:
    bucket_name: str
    object_name: str


def parse_gcs_uri(uri: str, *, require_object: bool = True) -> GcsUri:
    if not uri.startswith("gs://"):
        raise ValueError(f"URI GCS invalide: {uri}")

    bucket_name, separator, object_name = uri.removeprefix("gs://").partition("/")
    if not bucket_name:
        raise ValueError(f"URI GCS invalide, bucket manquant: {uri}")
    if require_object and (not separator or not object_name):
        raise ValueError(f"URI GCS invalide, objet manquant: {uri}")

    return GcsUri(bucket_name=bucket_name, object_name=object_name)


def as_directory_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    return prefix if prefix.endswith("/") else f"{prefix}/"
