"""x402 payment wiring: turns /preview into a pay-per-call endpoint.

This is the only file that knows about money. It configures:
  - the resource server (delegates payment verification/settlement to a
    facilitator over HTTP — this API never touches private keys or an RPC
    node directly),
  - the price/network/payout address for the protected route,
  - an x402 Bazaar discovery declaration, so agents (and the CDP facilitator
    that indexes the Bazaar) can find this endpoint and learn its input/
    output shape without a human reading docs.
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
}


def build_resource_server(settings: Settings) -> x402ResourceServer:
    facilitator = HTTPFacilitatorClient({"url": settings.facilitator_url})
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
                "Fetch Open Graph / meta metadata (title, description, image, "
                "favicon, canonical URL) for a public URL."
            ),
            "service_name": settings.app_name,
            "tags": ["link-preview", "metadata", "web", "scraping"],
            "extensions": discovery,
        }
    }
