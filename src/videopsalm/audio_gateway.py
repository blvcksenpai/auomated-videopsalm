"""Contracts for mixer audio input and connection health."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Protocol

from .providers import AudioChunk


class AudioHealth(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


@dataclass(frozen=True, slots=True)
class AudioStatus:
    health: AudioHealth
    device_id: str | None
    changed_at: datetime
    reason: str = ""


class AudioGateway(Protocol):
    async def chunks(self) -> AsyncIterator[AudioChunk]:
        """Yield live audio chunks until the gateway disconnects."""

    async def status(self) -> AsyncIterator[AudioStatus]:
        """Yield input health changes and reconnect state."""
