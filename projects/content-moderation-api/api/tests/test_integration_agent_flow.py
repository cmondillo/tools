"""End-to-end test of the real payment handshake, POST variant. Same
approach as link-preview-api's test of the same name - see that file for
the full explanation of why this is the strongest test in the suite.
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
_TEST_PRIVATE_KEY = "0x" + "22" * 32  # deterministic throwaway key, test-only


@respx.mock
@pytest.mark.asyncio
async def test_agent_pays_and_receives_moderation_result(capsys):
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
                "transaction": "0x" + "cd" * 32,
                "network": _settings.network,
                "payer": account.address,
            },
        )
    )

    app = create_app()
    exit_code = await agent_client.run(
        api_base="http://testserver",
        text="You are a bitch and an asshole.",
        private_key=_TEST_PRIVATE_KEY,
        network=_settings.network,
        inner_transport=httpx.ASGITransport(app=app),
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"flagged": true' in out
    assert '"bitch"' in out
    assert "Payment settled" in out
