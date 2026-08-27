"""Tests for the manual cache admin routes (POST/GET/DELETE /admin/cache).
Not x402-gated - bearer token auth via ADMIN_TOKEN, see app/main.py."""

from dataclasses import replace

import httpx
import pytest
import respx
from eth_account import Account
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

_TEST_PRIVATE_KEY = "0x" + "22" * 32  # deterministic throwaway key, test-only

_settings_no_token = get_settings()  # admin_token is None by default
_settings_with_token = replace(_settings_no_token, admin_token="s3cr3t")

_FACILITATOR_SUPPORTED = {
    "kinds": [
        {"x402_version": 2, "scheme": "exact", "network": _settings_no_token.network, "extra": None}
    ],
    "extensions": [],
    "signers": {},
}


def _mock_facilitator():
    respx.get(f"{_settings_no_token.facilitator_url}/supported").mock(
        return_value=httpx.Response(200, json=_FACILITATOR_SUPPORTED)
    )


@respx.mock
def test_admin_routes_are_503_when_token_unset():
    _mock_facilitator()
    client = TestClient(create_app(_settings_no_token))

    r1 = client.post("/admin/cache", json={"url": "https://example.com"})
    r2 = client.get("/admin/cache", params={"url": "https://example.com"})
    r3 = client.delete("/admin/cache", params={"url": "https://example.com"})

    assert r1.status_code == r2.status_code == r3.status_code == 503


@respx.mock
def test_admin_post_requires_correct_token():
    _mock_facilitator()
    client = TestClient(create_app(_settings_with_token))

    no_auth = client.post("/admin/cache", json={"url": "https://example.com"})
    assert no_auth.status_code == 401

    wrong_token = client.post(
        "/admin/cache",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert wrong_token.status_code == 401


@respx.mock
@pytest.mark.asyncio
async def test_admin_can_seed_a_url_a_real_paying_agent_then_receives(tmp_path):
    """The actual point of this feature: coinbase.com/dexscreener.com 403
    any scraper, so the normal fetch path can never populate them - but a
    manually seeded entry still gets served to a real, fully paying agent.
    No mocked origin fetch here on purpose: if the cache didn't actually
    serve the seeded entry, this test would try a real network fetch to
    coinbase.com and fail/hang, not silently pass."""
    account = Account.from_key(_TEST_PRIVATE_KEY)
    settings = replace(_settings_with_token, cache_db_path=str(tmp_path / "cache.db"))

    _mock_facilitator()
    respx.post(f"{settings.facilitator_url}/verify").mock(
        return_value=httpx.Response(200, json={"isValid": True, "payer": account.address})
    )
    respx.post(f"{settings.facilitator_url}/settle").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "transaction": "0x" + "cd" * 32,
                "network": settings.network,
                "payer": account.address,
            },
        )
    )

    app = create_app(settings)
    admin_headers = {"Authorization": "Bearer s3cr3t"}
    TestClient(app).post(
        "/admin/cache",
        json={
            "url": "https://coinbase.com",
            "title": "Coinbase",
            "description": "Manually seeded - Coinbase blocks scrapers.",
        },
        headers=admin_headers,
    )

    from x402 import x402Client
    from x402.http.clients.httpx import x402_httpx_transport
    from x402.mechanisms.evm.exact import ExactEvmScheme

    x402client = x402Client()
    x402client.register(settings.network, ExactEvmScheme(signer=account))
    transport = x402_httpx_transport(
        x402client, transport=httpx.ASGITransport(app=app)
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        response = await http.get("/preview", params={"url": "https://coinbase.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Coinbase"
    assert body["cached"] is True

    inspect = TestClient(app).get(
        "/admin/cache", params={"url": "https://coinbase.com"}, headers=admin_headers
    )
    assert inspect.json()["title"] == "Coinbase"


@respx.mock
def test_admin_get_404_for_unknown_url():
    _mock_facilitator()
    client = TestClient(create_app(_settings_with_token))
    response = client.get(
        "/admin/cache",
        params={"url": "https://never-seeded.example.com"},
        headers={"Authorization": "Bearer s3cr3t"},
    )
    assert response.status_code == 404


@respx.mock
def test_admin_delete_removes_entry(tmp_path):
    _mock_facilitator()
    settings = replace(_settings_with_token, cache_db_path=str(tmp_path / "cache.db"))
    client = TestClient(create_app(settings))
    headers = {"Authorization": "Bearer s3cr3t"}

    client.post("/admin/cache", json={"url": "https://example.com", "title": "X"}, headers=headers)

    delete = client.delete("/admin/cache", params={"url": "https://example.com"}, headers=headers)
    assert delete.status_code == 200
    assert delete.json()["removed"] is True

    delete_again = client.delete(
        "/admin/cache", params={"url": "https://example.com"}, headers=headers
    )
    assert delete_again.json()["removed"] is False

    inspect = client.get("/admin/cache", params={"url": "https://example.com"}, headers=headers)
    assert inspect.status_code == 404


@respx.mock
def test_admin_routes_hidden_from_public_openapi_schema():
    _mock_facilitator()
    client = TestClient(create_app(_settings_with_token))
    spec = client.get("/openapi.json").json()
    assert "/admin/cache" not in spec["paths"]
