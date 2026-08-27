"""Tests for the MCP interface. Same approach as link-preview-api's
test_mcp_server.py - see that file for why build_mcp_server() needs the
facilitator mocked before construction, not just before first call."""

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
    assert tools[0].name == "moderate_text"
    assert tools[0].inputSchema["required"] == ["text"]


@respx.mock
@pytest.mark.asyncio
async def test_call_without_payment_returns_correct_402_body():
    _mock_supported()
    mcp = build_mcp_server()

    result = await mcp.call_tool("moderate_text", {"text": "hello"})

    assert result.isError is True
    body = json.loads(result.content[0].text)
    assert body["error"] == "Payment Required"
    quote = body["accepts"][0]
    assert quote["payTo"] == _settings.pay_to_address
    assert quote["amount"] == "5000"  # $0.005 at 6 decimals
    assert body["extensions"]["bazaar"]["info"]["input"]["toolName"] == "moderate_text"


@respx.mock
def test_build_fails_loudly_if_facilitator_is_unreachable():
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    with pytest.raises(httpx.ConnectError):
        build_mcp_server()
