from typing import Protocol

from factory_writer.application.ports.object_storage import (
    ObjectStoragePort,
    StoredObjectFile,
)


class StyleGuideStoragePort(ObjectStoragePort, Protocol):
    async def get_object_file(self, storage_uri: str) -> StoredObjectFile | None: ...
