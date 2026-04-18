from dataclasses import dataclass


@dataclass(frozen=True)
class StyleGuideIngestionConfigPort:
    bucket_name: str
    draft_pack_prompt_name: str
    active_prompt_version: str
