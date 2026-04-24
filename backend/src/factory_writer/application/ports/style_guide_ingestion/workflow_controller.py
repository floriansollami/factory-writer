from typing import Protocol


class StyleGuideWorkflowControllerPort(Protocol):
    async def approve_style_pack(
        self,
        *,
        workflow_id: str,
        style_pack_id: str,
    ) -> None: ...

    async def reject_style_pack(
        self,
        *,
        workflow_id: str,
        style_pack_id: str,
    ) -> None: ...
