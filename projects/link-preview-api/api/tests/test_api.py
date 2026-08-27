"""API-level tests.

The paid route can't build a price quote without first confirming, via the
facilitator's /supported endpoint, that it actually backs the configured
network+scheme (see app/config.py). That's a real network call in
production; here it's mocked with respx so the suite is fast, deterministic,
and doesn't depend on a third-party service being reachable.

Each test builds its own app via create_app(): the x402 middleware caches
"have I synced with the facilitator yet" for the lifetime of the app
instance it's built into, so tests exercising that first-sync path need a
fresh instance rather than sharing the module-level app.
"""

import base64
import json

import httpx
import respx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

_settings = get_settings()

_FACILITATOR_SUPPORTED = {
    "kinds": [
        {"x402_version": 2, "scheme": "exact", "network": _settings.network, "extra": None}
    ],
    "extensions": [],
    "signers": {},
}


def test_healthz_is_free():
    """Health checks must never depend on the facilitator being reachable."""
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_favicon_is_free_and_is_a_png():
    """Directories like x402scan probe for a real /favicon.ico; must be free
    (not payment-gated) and an actual image, not a placeholder 200."""
    client = TestClient(create_app())
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_openapi_spec_declares_a_contact_email():
    """x402scan flags listings with no way to reach the operator; the public
    OpenAPI spec must carry one."""
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    contact = response.json()["info"]["contact"]
    assert contact["email"] == "abstracttokengen@gmail.com"


def test_free_routes_declare_no_security_requirement():
    """/healthz, /, and /favicon.ico must advertise security:[] in the OpenAPI
    spec so a directory that probes every path for a 402 treats them as
    free-by-design rather than flagging them as broken paid endpoints."""
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()
    for path in ("/healthz", "/", "/favicon.ico"):
        assert spec["paths"][path]["get"]["security"] == []


def test_root_is_free_and_describes_pricing():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol"] == "x402"
    assert "price" in body and "network" in body and "pay_to" in body


@respx.mock
def test_preview_requires_payment():
    """Hitting the paid endpoint with no payment must return 402, never data."""
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        return_value=httpx.Response(200, json=_FACILITATOR_SUPPORTED)
    )
    client = TestClient(create_app())

    response = client.get("/preview", params={"url": "https://example.com"})

    assert response.status_code == 402
    # x402 v2 carries the price quote in the Payment-Required header, base64(JSON).
    payment_required = json.loads(base64.b64decode(response.headers["payment-required"]))
    quote = payment_required["accepts"][0]
    assert quote["payTo"] == _settings.pay_to_address
    assert quote["network"] == _settings.network
    assert quote["amount"] == "10000"  # $0.01 at 6 decimals (USDC)
    # Bazaar discovery info is enriched with the real HTTP method at request time.
    assert payment_required["extensions"]["bazaar"]["info"]["input"]["method"] == "GET"


@respx.mock
def test_preview_returns_clean_error_when_facilitator_is_unreachable():
    """A facilitator outage/network failure must surface as a clean 503,
    never a raw 500 traceback leak."""
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    client = TestClient(create_app())

    response = client.get("/preview", params={"url": "https://example.com"})

    assert response.status_code == 503
    assert "error" in response.json()
