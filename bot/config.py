from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    database_path: str
    default_timezone: str
    extra_ca_bundle: str | None

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN is not set. Copy .env.example to .env and fill in your bot token."
            )
        return cls(
            bot_token=token,
            database_path=os.environ.get("DATABASE_PATH", "./data/bot.db"),
            default_timezone=os.environ.get("DEFAULT_TIMEZONE", "Europe/Moscow"),
            # Only needed behind a TLS-inspecting corporate/sandbox proxy that
            # re-signs outbound HTTPS with its own CA.
            extra_ca_bundle=os.environ.get("EXTRA_CA_BUNDLE", "").strip() or None,
        )
