from typing import Protocol

from factory_writer.application.ports.object_storage import ObjectStoragePort


class TechnicalSourceStoragePort(ObjectStoragePort, Protocol):
    pass
