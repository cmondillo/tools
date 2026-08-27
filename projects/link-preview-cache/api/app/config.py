"""Runtime configuration, loaded entirely from environment variables. Same
shape as link-preview-api's config.py - see that project for the full
rationale on the money-related settings.
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
    contact_email: str
    pay_to_address: str
    price_usd: str
    network: str
    facilitator_url: str
    cdp_api_key_id: str | None
    cdp_api_key_secret: str | None
    sync_facilitator_on_start: bool
    request_timeout: float
    max_response_bytes: int
    cache_db_path: str
    cache_ttl_seconds: float
    admin_token: str | None

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
        app_name=os.environ.get("APP_NAME", "Link Preview Cache API"),
        contact_email=os.environ.get("CONTACT_EMAIL", "abstracttokengen@gmail.com"),
        pay_to_address=os.environ.get(
            "X402_PAY_TO_ADDRESS", "0x000000000000000000000000000000000000dEaD"
        ),
        # Flat price, always - no cache-hit/cache-miss price split. x402 quotes
        # a price up front (before the handler runs), so it can't depend on
        # whether *this* request happens to hit the cache. Instead: one price,
        # lower than link-preview-api's $0.01, made sustainable *because* most
        # requests are cheap cache hits internally - see README and
        # potential/simulate_savings.py for why that holds up.
        price_usd=os.environ.get("X402_PRICE_USD", "$0.003"),
        network=os.environ.get("X402_NETWORK", "eip155:84532"),
        facilitator_url=os.environ.get("X402_FACILITATOR_URL", "https://x402.org/facilitator"),
        cdp_api_key_id=os.environ.get("CDP_API_KEY_ID"),
        cdp_api_key_secret=os.environ.get("CDP_API_KEY_SECRET"),
        sync_facilitator_on_start=_env_bool("X402_SYNC_FACILITATOR_ON_START", True),
        request_timeout=float(os.environ.get("PREVIEW_TIMEOUT_SECONDS", "8")),
        max_response_bytes=int(os.environ.get("PREVIEW_MAX_BYTES", str(2 * 1024 * 1024))),
        cache_db_path=os.environ.get("CACHE_DB_PATH", "./data/cache.db"),
        # 6h: long enough that a popular URL shared/looked-up repeatedly
        # across many agents in the same day mostly hits cache, short enough
        # that a page's OG metadata (title/image edits, etc.) doesn't go
        # stale for long if it changes.
        cache_ttl_seconds=float(os.environ.get("CACHE_TTL_SECONDS", str(6 * 3600))),
        # Bearer token for the /admin/cache routes (manual insert/inspect/
        # delete - see main.py). Unset by default: those routes then answer
        # 503 rather than silently accepting an empty/blank token as valid.
        admin_token=os.environ.get("ADMIN_TOKEN") or None,
    )
