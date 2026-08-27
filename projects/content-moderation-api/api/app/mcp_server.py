"""MCP server: the same product, sold over MCP instead of raw HTTP.

Same pattern as link-preview-api's mcp_server.py - see that file for the
detailed why. Requires mcp<2 (see requirements.txt comment).

Run standalone:
    python -m app.mcp_server
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
from .moderation import ModerationError, moderate
from .payment import _EXAMPLE_OUTPUT, build_resource_server

logger = logging.getLogger("content_moderation_mcp")

_TOOL_NAME = "moderate_text"


def build_mcp_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()

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
                        "description": "Text to check. Max 5000 characters.",
                    }
                },
                "required": ["text"],
            },
            example={"text": "You are a jerk."},
            output=OutputConfig(example=_EXAMPLE_OUTPUT),
        )
    )

    mcp = FastMCP(settings.app_name)
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
