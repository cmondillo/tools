"""x402 payment wiring: turns /moderate into a pay-per-call endpoint.

This is the only file that knows about money. Same pattern as
link-preview-api's payment.py: configures the resource server (delegates
verification/settlement to a facilitator over HTTP), the price/network/
payout address, and an x402 Bazaar discovery declaration.
"""

from __future__ import annotations

from x402 import x402ResourceServer
from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from .config import Settings

_EXAMPLE_OUTPUT = {
    "flagged": True,
    "matches": [{"term": "asshole", "start": 10, "end": 17}],
    "match_count": 1,
    "redacted_text": "You are a *******.",
}


def _facilitator_config(settings: Settings) -> dict:
    """Plain URL by default (x402.org, testnet-only, no auth). Once
    CDP_API_KEY_ID/CDP_API_KEY_SECRET are both set (mainnet), switch to the
    CDP facilitator - identical logic to link-preview-api's payment.py."""
    if settings.use_cdp_facilitator:
        from cdp.x402 import create_facilitator_config

        return create_facilitator_config(settings.cdp_api_key_id, settings.cdp_api_key_secret)
    return {"url": settings.facilitator_url}


def build_resource_server(settings: Settings) -> x402ResourceServer:
    facilitator = HTTPFacilitatorClient(_facilitator_config(settings))
    server = x402ResourceServer(facilitator)
    server.register(settings.network, ExactEvmServerScheme())
    return server


def build_routes_config(settings: Settings) -> dict:
    discovery = declare_discovery_extension(
        input={"text": "You are a jerk."},
        input_schema={
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to check for profanity/explicit terms. Max 50,000 characters.",
                }
            },
            "required": ["text"],
        },
        body_type="json",
        output=OutputConfig(example=_EXAMPLE_OUTPUT),
    )

    return {
        "POST /moderate": {
            "accepts": [
                {
                    "scheme": "exact",
                    "payTo": settings.pay_to_address,
                    "price": settings.price_usd,
                    "network": settings.network,
                }
            ],
            "description": (
                "Check text for profanity/explicit terms (wordlist-based, with basic "
                "leetspeak/obfuscation detection); returns a flag, matched terms, and "
                "a redacted version."
            ),
            "service_name": settings.app_name,
            "tags": ["moderation", "profanity-filter", "content-safety", "agents"],
            "extensions": discovery,
        }
    }
