"""MCP server: the same product, sold over MCP instead of raw HTTP. Same
pattern as content-moderation-api's mcp_server.py (mountable at /mcp on the
same deployment, or runnable standalone over stdio). Requires mcp<2 (see
requirements.txt comment).

Run standalone:
    python -m app.mcp_server
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from x402 import x402ResourceServer
from x402.extensions.bazaar import (
    DeclareMcpDiscoveryConfig,
    OutputConfig,
    declare_mcp_discovery_extension,
)
from x402.mcp.server import create_payment_wrapper
from x402.schemas.config import ResourceConfig

from . import cache
from .config import Settings, get_settings
from .payment import _EXAMPLE_OUTPUT, build_resource_server
from .preview import PreviewError, fetch_preview

logger = logging.getLogger("link_preview_cache_mcp")

_TOOL_NAME = "preview_url"


def build_mcp_server(
    settings: Settings | None = None,
    resource_server: x402ResourceServer | None = None,
) -> FastMCP:
    """`resource_server` lets a caller that already built and initialized one
    (main.py, mounting this alongside the HTTP app) pass it in instead of a
    second facilitator round-trip. Standalone use (`python -m app.mcp_server`)
    builds and eagerly initializes its own."""
    settings = settings or get_settings()

    if resource_server is None:
        resource_server = build_resource_server(settings)
        resource_server.initialize()

    accepts = resource_server.build_payment_requirements(
        ResourceConfig(
            scheme="exact",
            pay_to=settings.pay_to_address,
            price=settings.price_usd,
            network=settings.network,
        )
    )

    extensions = declare_mcp_discovery_extension(
        DeclareMcpDiscoveryConfig(
            tool_name=_TOOL_NAME,
            description=(
                "Fetch Open Graph / meta metadata (title, description, image, favicon, "
                "canonical URL) for a public URL - served from a shared cache when "
                "available."
            ),
            input_schema={
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "Public http(s) URL to fetch metadata for.",
                    }
                },
                "required": ["url"],
            },
            example={"url": "https://example.com/blog/hello-world"},
            output=OutputConfig(example=_EXAMPLE_OUTPUT),
        )
    )

    # streamable_http_path="/" + transport_security disabled: see
    # content-moderation-api/api/app/mcp_server.py for the full rationale
    # (avoids landing at /mcp/mcp when mounted, and avoids 421-ing every
    # real request from FastMCP's localhost-only DNS-rebinding default).
    mcp = FastMCP(
        settings.app_name,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    payment = create_payment_wrapper(resource_server, accepts=accepts, extensions=extensions)

    @mcp.tool(name=_TOOL_NAME)
    @payment
    async def preview_url(url: str) -> dict:
        """Fetch Open Graph / meta metadata for a public URL. Costs $0.003 USDC on Base."""
        try:
            cached = cache.get(settings.cache_db_path, url, ttl_seconds=settings.cache_ttl_seconds)
            if cached is not None:
                return {**cached, "cached": True}
            result = await fetch_preview(
                url, timeout=settings.request_timeout, max_bytes=settings.max_response_bytes
            )
            data = result.to_dict()
            cache.set(settings.cache_db_path, url, data)
        except PreviewError as exc:
            return {"error": exc.message}
        return {**data, "cached": False}

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_mcp_server().run()


if __name__ == "__main__":
    main()
