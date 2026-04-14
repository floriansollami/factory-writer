from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# SOTA: Les imports locaux liés au domaine ou aux activités DOIVENT se faire à l'intérieur
# ou via un pattern sûr, mais pour les data classes, c'est OK en haut.
from domain.temporal_models import StyleGuideIngestionInput, StyleGuideIngestionOutput

# SOTA: Pour les workflows, les activités doivent être importées via un stub ou directement si le package
# est isolé. Temporal recommande `with workflow.unsafe.imports_passed_through()` pour éviter les
# erreurs de non-déterminisme pures Python, ou on peut juste les importer dynamiquement.
with workflow.unsafe.imports_passed_through():
    from temporal.activities.style_guide_activities import (
        extract_rules_litellm_activity,
        poll_docai_completion_activity,
        process_layout_chunks_activity,
        promote_style_pack_activity,
        trigger_docai_batch_activity,
        update_source_status_activity,
        update_source_status_erreur_activity,
    )


@workflow.defn(name="StyleGuideIngestionWorkflow")
class StyleGuideIngestionWorkflow:
    def __init__(self) -> None:
        self.is_approved: bool | None = None
        self.compensations: list[str] = []

    @workflow.run
    async def run(self, input: StyleGuideIngestionInput) -> StyleGuideIngestionOutput:
        try:
            # 1. Update Database Status (EN_COURS)
            await workflow.execute_activity(
                update_source_status_activity,
                args=[input.source_id],
                start_to_close_timeout=timedelta(minutes=1),
            )
            # SOTA 2026 : Enregistrement de la compensation (Rollback en cas de crash plus bas)
            self.compensations.append("update_status_erreur")

            # 2. Trigger Extraction GCS -> Document AI
            gcs_output_path = await workflow.execute_activity(
                trigger_docai_batch_activity,
                args=[input.file_uri],
                start_to_close_timeout=timedelta(minutes=5),
            )

            # 3. Polling Job Document AI
            await workflow.execute_activity(
                poll_docai_completion_activity,
                args=[gcs_output_path],
                start_to_close_timeout=timedelta(hours=2),  # Polling long SOTA
            )

            # 4. Upsert Chunks en DB
            chunk_ids = await workflow.execute_activity(
                process_layout_chunks_activity,
                args=[gcs_output_path],
                start_to_close_timeout=timedelta(minutes=5),
            )

            # 5. Extraction LLM & Generation du Pack Brouillon (Structured Output)
            # SOTA 2026 : Protection contre les API LLM via RetryPolicy strict (limiter les coûts)
            draft_pack_id = await workflow.execute_activity(
                extract_rules_litellm_activity,
                args=[chunk_ids],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            # 6. Attente Asynchrone Approbation Humaine (Signal)
            # Le workflow va se suspendre nativement et ne consommer aucune ressource !
            workflow.logger.info("⏳ Waiting for human approval signal...")
            try:
                await workflow.wait_condition(
                    lambda: self.is_approved is not None, timeout=timedelta(days=7)
                )
            except Exception: # Timeout ou autre
                pass

            if not self.is_approved:
                raise Exception("L'expert de marque (Sophie) a rejeté le Pack Draft ou timeout expiré.")

            # 7. Promotion en Pack ACTIF
            await workflow.execute_activity(
                promote_style_pack_activity,
                args=[draft_pack_id],
                start_to_close_timeout=timedelta(minutes=1),
            )

            workflow.logger.info("✅ StyleGuideIngestionWorkflow completed successfully!")
            return StyleGuideIngestionOutput(status="success", pack_id=draft_pack_id)

        except Exception as e:
            workflow.logger.error(f"❌ Workflow failed: {str(e)}. Triggering SAGA Compensations.")
            # === Saga Pattern Compensation ===
            for comp in reversed(self.compensations):
                if comp == "update_status_erreur":
                    await workflow.execute_activity(
                        update_source_status_erreur_activity,
                        args=[input.source_id],
                        start_to_close_timeout=timedelta(minutes=1),
                    )
            # On relance l'erreur pour que l'historique Temporal l'affiche en Failed
            raise e

    @workflow.signal
    def approve_pack(self, approved: bool) -> None:
        """
        Signal Temporal. Peut être appelé via un bouton dans le back-office.
        """
        self.is_approved = approved
