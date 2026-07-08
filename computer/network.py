"""Network capability."""

from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Network:
    def hostname(self) -> str:
        return socket.gethostname()

    def resolve(self, host: str) -> list[str]:
        return list({item[4][0] for item in socket.getaddrinfo(host, None)})
