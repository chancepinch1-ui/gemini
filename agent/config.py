"""Configuration loaded from environment variables.

Kept dependency-free and explicit so the agent is easy to operate:
every knob is a single env var with a sane default.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    interval_seconds: int
    history_size: int
    log_size: int

    @staticmethod
    def from_env() -> "Config":
        return Config(
            host=os.environ.get("AGENT_HOST", "127.0.0.1"),
            port=int(os.environ.get("AGENT_PORT", "8765")),
            interval_seconds=int(os.environ.get("AGENT_INTERVAL", "30")),
            history_size=int(os.environ.get("AGENT_HISTORY_SIZE", "50")),
            log_size=int(os.environ.get("AGENT_LOG_SIZE", "200")),
        )
