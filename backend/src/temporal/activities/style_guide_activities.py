import asyncio
import structlog
from temporalio import activity

logger = structlog.get_logger(__name__)

# Activité 1 : Update Status
@activity.defn(name="update_source_status_activity")
async def update_source_status_activity(source_id: str) -> None:
    logger.info("Activity [A1] : update_source_status_activity started", source_id=source_id)
    await asyncio.sleep(1) # Simulation de l'appel DB
    logger.info("Activity [A1] : update_source_status_activity finished")

# Activité 1 (Compensation) : Update Status Rollback
@activity.defn(name="update_source_status_erreur_activity")
async def update_source_status_erreur_activity(source_id: str) -> None:
    logger.error("Activity [A1-Rollback] : update_source_status_erreur_activity started", source_id=source_id)
    await asyncio.sleep(1) # Simulation de l'appel DB
    logger.error("Activity [A1-Rollback] : update_source_status_erreur_activity finished")

# Activité 2 : Trigger Document AI
@activity.defn(name="trigger_docai_batch_activity")
async def trigger_docai_batch_activity(file_uri: str) -> str:
    logger.info("Activity [A2] : trigger_docai_batch_activity started", file_uri=file_uri)
    await asyncio.sleep(1)
    gcs_output_path = f"gs://fake-output-bucket/docai-extracts/{file_uri.split('/')[-1]}.json"
    logger.info("Activity [A2] : triggered successfully", gcs_output_path=gcs_output_path)
    return gcs_output_path

# Activité 3 : Poll Document AI Completion
@activity.defn(name="poll_docai_completion_activity")
async def poll_docai_completion_activity(gcs_output_path: str) -> None:
    logger.info("Activity [A3] : poll_docai_completion_activity started", target=gcs_output_path)
    # On simule un long polling court
    for i in range(3):
        logger.debug(f"Polling Document AI LRO... {i+1}/3")
        await asyncio.sleep(1)
        activity.heartbeat(f"progress {i+1}/3")
    logger.info("Activity [A3] : Document AI parsing completed")

# Activité 4 : Process Layout Chunks
@activity.defn(name="process_layout_chunks_activity")
async def process_layout_chunks_activity(gcs_output_path: str) -> list[str]:
    logger.info("Activity [A4] : process_layout_chunks_activity started", target=gcs_output_path)
    await asyncio.sleep(1)
    chunk_ids = ["chunk-uuid-1", "chunk-uuid-2"]
    logger.info("Activity [A4] : chunks saved to Postgres", chunks_count=len(chunk_ids))
    return chunk_ids

# Activité 5 : Extract Rules LiteLLM
@activity.defn(name="extract_rules_litellm_activity")
async def extract_rules_litellm_activity(chunk_ids: list[str]) -> str:
    logger.info("Activity [A5] : extract_rules_litellm_activity started", input_chunks=len(chunk_ids))
    await asyncio.sleep(2) # Simulation de l'appel LiteLLM
    draft_pack_id = "pack-uuid-draft-litellm"
    logger.info("Activity [A5] : LiteLLM extraction success", draft_pack_id=draft_pack_id)
    return draft_pack_id

# Activité 6 : Promote Style Pack
@activity.defn(name="promote_style_pack_activity")
async def promote_style_pack_activity(draft_pack_id: str) -> None:
    logger.info("Activity [A6] : promote_style_pack_activity started", pack_id=draft_pack_id)
    await asyncio.sleep(1)
    logger.info("Activity [A6] : Style pack promoted to ACTIVE successfully")
