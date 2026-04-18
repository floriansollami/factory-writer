import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StyleGuideSourceFile:
    uri: str
    generation: str
    metageneration: str


class StyleGuideStoragePort(Protocol):
    async def get_source_file(self, file_uri: str) -> StyleGuideSourceFile | None: ...

    async def has_parser_result(self, result_uri: str) -> bool: ...

    def build_parser_result_uri(
        self, input_uri: str, extraction_type: str, source_id: uuid.UUID, generation: str
    ) -> str: ...
