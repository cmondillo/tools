"""API-level tests. Same respx-mocked-facilitator approach as
link-preview-api's test_api.py - see that file for why."""

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
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_is_free_and_describes_pricing():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol"] == "x402"
    assert "price" in body and "network" in body and "pay_to" in body


def test_favicon_is_free_and_is_a_png():
    client = TestClient(create_app())
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_openapi_spec_declares_a_contact_email():
    client = TestClient(create_app())
    response = client.get("/openapi.json")
    contact = response.json()["info"]["contact"]
    assert contact["email"] == _settings.contact_email


def test_free_routes_declare_no_security_requirement():
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()
    for path in ("/healthz", "/", "/favicon.ico"):
        assert spec["paths"][path]["get"]["security"] == []


@respx.mock
def test_moderate_requires_payment():
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        return_value=httpx.Response(200, json=_FACILITATOR_SUPPORTED)
    )
    client = TestClient(create_app())

    response = client.post("/moderate", json={"text": "hello"})

    assert response.status_code == 402
    payment_required = json.loads(base64.b64decode(response.headers["payment-required"]))
    quote = payment_required["accepts"][0]
    assert quote["payTo"] == _settings.pay_to_address
    assert quote["network"] == _settings.network
    assert quote["amount"] == "5000"  # $0.005 at 6 decimals (USDC)


@respx.mock
def test_moderate_returns_clean_error_when_facilitator_is_unreachable():
    respx.get(f"{_settings.facilitator_url}/supported").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    client = TestClient(create_app())

    response = client.post("/moderate", json={"text": "hello"})

    assert response.status_code == 503
    assert "error" in response.json()
