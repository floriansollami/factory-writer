from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from factory_writer.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Client | None = None
_client_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    """
    Client Temporal mutualisé pour API et workers.

    Le Data Converter Pydantic est imposé partout pour garder un contrat
    homogène entre start_workflow, signal et exécution worker.
    """
    global _client

    if _client is not None:
        return _client

    async with _client_lock:
        if _client is not None:
            return _client

        settings = get_settings()
        logger.info(
            "Connecting to Temporal at %s (namespace=%s)",
            settings.temporal.address,
            settings.temporal.namespace,
        )
        _client = await Client.connect(
            settings.temporal.address,
            namespace=settings.temporal.namespace,
            api_key=settings.temporal.api_key,
            data_converter=pydantic_data_converter,
        )
        logger.info("Connected to Temporal")
        return _client
