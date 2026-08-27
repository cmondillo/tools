"""x402 payment wiring: turns /preview into a pay-per-call endpoint. Same
pattern as link-preview-api's payment.py - single flat price, no dynamic
per-request pricing (see config.py for why).
"""

from __future__ import annotations

from x402 import x402ResourceServer
from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from .config import Settings

_EXAMPLE_OUTPUT = {
    "url": "https://example.com/blog/hello-world",
    "final_url": "https://example.com/blog/hello-world",
    "title": "Hello World",
    "description": "A short description of the page, from its meta tags.",
    "image": "https://example.com/og-image.png",
    "favicon": "https://example.com/favicon.ico",
    "site_name": "Example",
    "canonical_url": "https://example.com/blog/hello-world",
    "content_type": "text/html; charset=utf-8",
    "cached": True,
}


def _facilitator_config(settings: Settings) -> dict:
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
        input={"url": "https://example.com/blog/hello-world"},
        input_schema={
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Public http(s) URL to fetch Open Graph / meta metadata for.",
                }
            },
            "required": ["url"],
        },
        output=OutputConfig(example=_EXAMPLE_OUTPUT),
    )

    return {
        "GET /preview": {
            "accepts": [
                {
                    "scheme": "exact",
                    "payTo": settings.pay_to_address,
                    "price": settings.price_usd,
                    "network": settings.network,
                }
            ],
            "description": (
                "Fetch Open Graph / meta metadata (title, description, image, favicon, "
                "canonical URL) for a public URL - served from a shared cache when "
                "available, which is what keeps the price below a fresh-fetch-every-time "
                "service. Response includes a 'cached' field."
            ),
            "service_name": settings.app_name,
            "tags": ["link-preview", "metadata", "web", "scraping", "cache"],
            "extensions": discovery,
        }
    }
