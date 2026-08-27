"""End-to-end test of the real payment handshake AND the cache behavior:
sample agent client <-> live FastAPI app, driven entirely in-process over an
ASGI transport. Same pattern as link-preview-api's version of this test,
plus the actual point of this whole project: the second call for the same
URL must be served from cache, not a second fetch.
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
async def test_agent_pays_twice_second_call_hits_cache_not_a_second_fetch(capsys, tmp_path):
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
    # Mocked once - if the app called it a second time (i.e. the cache
    # didn't actually work), respx would error on the unexpected extra call.
    origin_route = respx.get("https://example.com/article").mock(
        return_value=httpx.Response(200, content=_TARGET_HTML, headers={"content-type": "text/html"})
    )

    from dataclasses import replace

    app = create_app(replace(get_settings(), cache_db_path=str(tmp_path / "cache.db")))
    exit_code = await agent_client.run(
        api_base="http://testserver",
        target_url="https://example.com/article",
        private_key=_TEST_PRIVATE_KEY,
        network=_settings.network,
        inner_transport=httpx.ASGITransport(app=app),
    )

    assert exit_code == 0
    assert origin_route.call_count == 1  # the real fetch happened exactly once

    out = capsys.readouterr().out
    assert out.count('"title": "Integration Test Page"') == 2  # both calls got the data
    assert "cached=False" in out  # first call: real fetch
    assert "cached=True" in out  # second call: served from cache
    assert out.count("Payment settled") == 2  # both calls were paid, same price either way
