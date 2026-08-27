"""MCP server: the same product, sold over MCP instead of raw HTTP.

Coding agents (Claude Desktop, Claude Code, and most MCP-native tools)
discover and call tools over MCP directly - a more direct distribution
channel than an agent having to already know to speak raw x402/HTTP.
Same price, same wallet, same facilitator as the HTTP API; this is a
second interface onto the identical product, not a separate one.

Run standalone:
    python -m app.mcp_server

Add to Claude Desktop / Claude Code as an MCP server pointed at this
command (stdio transport, the FastMCP default).
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from x402.extensions.bazaar import (
    DeclareMcpDiscoveryConfig,
    OutputConfig,
    declare_mcp_discovery_extension,
)
from x402.mcp.server import create_payment_wrapper
from x402.schemas.config import ResourceConfig

from .config import Settings, get_settings
from .payment import _EXAMPLE_OUTPUT, build_resource_server
from .preview import PreviewError, fetch_preview

logger = logging.getLogger("link_preview_mcp")

_TOOL_NAME = "preview_url"


def build_mcp_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()

    resource_server = build_resource_server(settings)
    # Unlike the FastAPI app (which builds requirements lazily, per request,
    # via a declarative routes config), the MCP payment wrapper wants an
    # already-built list[PaymentRequirements] up front - so initialize()
    # (the one facilitator round trip that confirms it backs this
    # network+scheme) has to happen here at startup, not on first call.
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
                "Fetch Open Graph / meta metadata (title, description, image, "
                "favicon, canonical URL) for a public URL."
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

    mcp = FastMCP(settings.app_name)
    payment = create_payment_wrapper(resource_server, accepts=accepts, extensions=extensions)

    @mcp.tool(name=_TOOL_NAME)
    @payment
    async def preview_url(url: str) -> dict:
        """Fetch Open Graph / meta metadata for a public URL. Costs $0.01 USDC on Base."""
        try:
            result = await fetch_preview(
                url, timeout=settings.request_timeout, max_bytes=settings.max_response_bytes
            )
        except PreviewError as exc:
            return {"error": exc.message}
        return result.to_dict()

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_mcp_server().run()


if __name__ == "__main__":
    main()
