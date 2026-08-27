"""Tests for the MCP interface (app/mcp_server.py) - the same product sold
over MCP instead of raw HTTP. Same respx-mocked-facilitator approach as the
HTTP tests, so this runs fully offline and deterministically.

Unlike the FastAPI app, build_mcp_server() calls resource_server.initialize()
eagerly (the MCP payment wrapper needs an already-built accepts list, not a
lazy per-request one) - so every test here needs the facilitator mocked
before construction, not just before the first tool call.
"""

import json

import httpx
import pytest
import respx

from app.config import get_settings
from app.mcp_server import build_mcp_server

_settings = get_settings()

_FACILITATOR_SUPPORTED = {
    "kinds": [
        {"x402_version": 2, "scheme": "exact", "network": _settings.network, "extra": None}
    ],
    "extensions": [],
    "signers": {},
}


def _mock_supported():
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        return_value=httpx.Response(200, json=_FACILITATOR_SUPPORTED)
    )


@respx.mock
@pytest.mark.asyncio
async def test_tool_is_registered_with_correct_schema():
    _mock_supported()
    mcp = build_mcp_server()

    tools = await mcp.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "preview_url"
    assert tools[0].inputSchema["required"] == ["url"]


@respx.mock
@pytest.mark.asyncio
async def test_call_without_payment_returns_correct_402_body():
    _mock_supported()
    mcp = build_mcp_server()

    result = await mcp.call_tool("preview_url", {"url": "https://example.com"})

    assert result.isError is True
    body = json.loads(result.content[0].text)
    assert body["error"] == "Payment Required"
    quote = body["accepts"][0]
    assert quote["payTo"] == _settings.pay_to_address
    assert quote["network"] == _settings.network
    assert quote["amount"] == "10000"  # $0.01 at 6 decimals (USDC)
    # The MCP Bazaar discovery extension, not the HTTP one - same idea,
    # different resource type ("mcp" instead of "http").
    assert body["extensions"]["bazaar"]["info"]["input"]["type"] == "mcp"
    assert body["extensions"]["bazaar"]["info"]["input"]["toolName"] == "preview_url"


@respx.mock
def test_build_fails_loudly_if_facilitator_is_unreachable():
    """No silent fallback: if the facilitator can't confirm it backs our
    network+scheme at startup, building the server should fail clearly
    rather than serve a tool that can never actually be paid."""
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    with pytest.raises(httpx.ConnectError):
        build_mcp_server()
