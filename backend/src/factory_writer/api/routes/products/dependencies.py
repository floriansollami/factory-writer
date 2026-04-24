from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client

from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.product_repository import (
    ProductRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.infrastructure.gcp.storage_client import StorageClient
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.sku_lifecycle.starter import TemporalProductLifecycleWorkflowStarter


async def get_product_read_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> ProductTechnicalIngestionService:
    settings = get_settings()
    return ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
    )


async def get_product_upload_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> ProductTechnicalIngestionService:
    settings = get_settings()
    return ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
        storage=StorageClient(settings),
    )


async def get_product_workflow_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    temporal_client: Client = Depends(get_temporal_client),
) -> ProductTechnicalIngestionService:
    settings = get_settings()
    return ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
        storage=StorageClient(settings),
        workflow_starter=TemporalProductLifecycleWorkflowStarter(temporal_client),
    )
