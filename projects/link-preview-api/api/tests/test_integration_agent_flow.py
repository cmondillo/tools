"""End-to-end test of the real payment handshake: sample agent client <->
live FastAPI app, driven entirely in-process over an ASGI transport (no
sandboxed egress needed for the app<->agent leg).

Only the facilitator's HTTP boundary is mocked (via respx) — everything
else is the real, shipped code path: the agent really signs an EIP-3009
payment authorization with a real (test) private key, the server really
runs its x402 middleware and route handler, and preview.py really parses
HTML it fetched. This is the strongest test in the suite: if the wiring
between agent_client.py and app/ ever drifts, this is what catches it.
"""

import sys
from pathlib import Path

import httpx
import pytest
import respx
from eth_account import Account

from app.config import get_settings
from app.main import create_app

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "automation-client"))
import agent_client  # noqa: E402

_settings = get_settings()
_TEST_PRIVATE_KEY = "0x" + "11" * 32  # deterministic throwaway key, test-only

_TARGET_HTML = """
<html><head>
  <meta property="og:title" content="Integration Test Page" />
  <meta property="og:description" content="Fetched for real by preview.py." />
</head><body></body></html>
"""


@respx.mock
@pytest.mark.asyncio
async def test_agent_pays_and_receives_preview(capsys):
    account = Account.from_key(_TEST_PRIVATE_KEY)

    respx.get(f"{_settings.facilitator_url}/supported").mock(
        return_value=httpx.Response(
            200,
            json={
                "kinds": [
                    {
                        "x402_version": 2,
                        "scheme": "exact",
                        "network": _settings.network,
                        "extra": None,
                    }
                ],
                "extensions": [],
                "signers": {},
            },
        )
    )
    respx.post(f"{_settings.facilitator_url}/verify").mock(
        return_value=httpx.Response(200, json={"isValid": True, "payer": account.address})
    )
    respx.post(f"{_settings.facilitator_url}/settle").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "transaction": "0x" + "ab" * 32,
                "network": _settings.network,
                "payer": account.address,
            },
        )
    )
    respx.get("https://example.com/article").mock(
        return_value=httpx.Response(200, content=_TARGET_HTML, headers={"content-type": "text/html"})
    )

    app = create_app()
    exit_code = await agent_client.run(
        api_base="http://testserver",
        target_url="https://example.com/article",
        private_key=_TEST_PRIVATE_KEY,
        network=_settings.network,
        inner_transport=httpx.ASGITransport(app=app),
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"title": "Integration Test Page"' in out
    assert "Payment settled" in out
