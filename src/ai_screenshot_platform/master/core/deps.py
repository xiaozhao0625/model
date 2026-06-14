from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class MemoryRedisClient:
    values: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def get(self, key: str) -> Any:
        return self.values.get(key)


class RedisClient:
    def __init__(self, redis_url: str, timeout: float = 0.5) -> None:
        parsed = urlparse(redis_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 6379
        self.timeout = timeout

    def set(self, key: str, value: Any) -> None:
        self._command("SET", key, str(value))

    def get(self, key: str) -> str | None:
        response = self._command("GET", key)
        if response.startswith("$-1"):
            return None
        if response.startswith("$"):
            return response.split("\r\n", 2)[1]
        return response

    def _command(self, *parts: str) -> str:
        payload = self._encode(parts)
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(payload)
            return sock.recv(4096).decode("utf-8", errors="replace")

    @staticmethod
    def _encode(parts: tuple[str, ...]) -> bytes:
        chunks = [f"*{len(parts)}\r\n"]
        for part in parts:
            encoded = part.encode("utf-8")
            chunks.append(f"${len(encoded)}\r\n")
            chunks.append(part)
            chunks.append("\r\n")
        return "".join(chunks).encode("utf-8")
