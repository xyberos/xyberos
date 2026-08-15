"""Configuration and authentication for the texttools integration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    """Runtime configuration for the texttools integration."""

    auth_token: str | None = None
    base_url: str = "https://api.texttools.example.com"
    timeout: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from TEXTTOOLS_* environment variables."""
        prefix = "TEXTTOOLS"
        return cls(
            auth_token=os.getenv(f"{prefix}_TOKEN") or os.getenv(f"{prefix}_API_KEY"),
            base_url=os.getenv(f"{prefix}_BASE_URL", cls.base_url),
        )
