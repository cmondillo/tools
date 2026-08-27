"""MCP server: the same product, sold over MCP instead of raw HTTP.

Same pattern as link-preview-api's mcp_server.py - see that file for the
detailed why. Requires mcp<2 (see requirements.txt comment).

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

from .config import Settings, get_settings
from .moderation import ModerationError, moderate
from .payment import _EXAMPLE_OUTPUT, build_resource_server

logger = logging.getLogger("content_moderation_mcp")

_TOOL_NAME = "moderate_text"


def build_mcp_server(
    settings: Settings | None = None,
    resource_server: x402ResourceServer | None = None,
) -> FastMCP:
    """`resource_server` lets a caller that already built and initialized one
    (main.py, mounting this alongside the HTTP app on the same deployment)
    pass it in instead of paying for a second facilitator round-trip and
    silently ignoring `sync_facilitator_on_start`. Standalone use (`python -m
    app.mcp_server`) has no other resource_server to share, so it still
    builds and eagerly initializes its own here."""
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
                "Check text for profanity/explicit terms (wordlist-based, with basic "
                "leetspeak/obfuscation detection); returns a flag, matched terms, and "
                "a redacted version."
            ),
            input_schema={
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to check. Max 50,000 characters.",
                    }
                },
                "required": ["text"],
            },
            example={"text": "You are a jerk."},
            output=OutputConfig(example=_EXAMPLE_OUTPUT),
        )
    )

    # streamable_http_path="/": when this server is mounted under /mcp in
    # main.py (so it's reachable at the API's own public URL, not a separate
    # deployment), FastMCP would otherwise register its route at /mcp too,
    # landing at /mcp/mcp. Irrelevant for standalone stdio use (`python -m
    # app.mcp_server`).
    #
    # transport_security: FastMCP defaults to DNS-rebinding protection with
    # an allowed_hosts list of just localhost - meant for a server that's
    # only supposed to be reachable from the same machine (e.g. a browser
    # extension talking to a local process). This server is deliberately
    # public at a real domain, so that default would 421 every real
    # request. The actual trust boundary here is the x402 payment gate on
    # every tool call, not the Host header, so disable it explicitly rather
    # than hardcode/maintain a domain allowlist.
    mcp = FastMCP(
        settings.app_name,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    payment = create_payment_wrapper(resource_server, accepts=accepts, extensions=extensions)

    @mcp.tool(name=_TOOL_NAME)
    @payment
    async def moderate_text(text: str) -> dict:
        """Check text for profanity/explicit terms. Costs $0.005 USDC on Base."""
        try:
            result = moderate(text)
        except ModerationError as exc:
            return {"error": exc.message}
        return result.to_dict()

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_mcp_server().run()


if __name__ == "__main__":
    main()
