"""Cached Temporal client (pydantic data converter) shared by API and worker."""

import asyncio

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from app.config import get_settings

_client: Client | None = None
_lock = asyncio.Lock()


async def get_client() -> Client:
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                s = get_settings()
                _client = await asyncio.wait_for(
                    Client.connect(s.temporal_address, namespace=s.temporal_namespace,
                                   data_converter=pydantic_data_converter),
                    timeout=5,
                )
    return _client


def reset_client() -> None:
    global _client
    _client = None
