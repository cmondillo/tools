"""Runtime configuration, loaded entirely from environment variables.

Nothing here is hard-coded for one environment: the same image runs against
Base Sepolia (testnet, safe default) or Base mainnet (real money) purely by
changing env vars - see ../.env.example for every knob and what it does.
Same shape as link-preview-api's config.py by design - one pattern reused
across the portfolio, not reinvented per project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional: load a local .env file in dev if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    app_name: str
    pay_to_address: str
    price_usd: str
    network: str
    facilitator_url: str
    cdp_api_key_id: str | None
    cdp_api_key_secret: str | None
    sync_facilitator_on_start: bool
    contact_email: str

    @property
    def use_cdp_facilitator(self) -> bool:
        return bool(self.cdp_api_key_id and self.cdp_api_key_secret)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    return Settings(
        app_name=os.environ.get("APP_NAME", "Content Moderation API"),
        pay_to_address=os.environ.get(
            "X402_PAY_TO_ADDRESS", "0x000000000000000000000000000000000000dEaD"
        ),
        price_usd=os.environ.get("X402_PRICE_USD", "$0.005"),
        # eip155:84532 = Base Sepolia (testnet). eip155:8453 = Base mainnet (real money).
        network=os.environ.get("X402_NETWORK", "eip155:84532"),
        facilitator_url=os.environ.get(
            "X402_FACILITATOR_URL", "https://x402.org/facilitator"
        ),
        cdp_api_key_id=os.environ.get("CDP_API_KEY_ID"),
        cdp_api_key_secret=os.environ.get("CDP_API_KEY_SECRET"),
        sync_facilitator_on_start=_env_bool("X402_SYNC_FACILITATOR_ON_START", True),
        contact_email=os.environ.get("CONTACT_EMAIL", "abstracttokengen@gmail.com"),
    )
