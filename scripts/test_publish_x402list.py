"""Tests for publish_x402list.py against x402-list.com's real, documented
API shape (not scraped) - respx-mocked so this runs offline and never
touches the real (paid, rate-limited) endpoint.
"""

import httpx
import pytest
import respx

from publish_x402list import SUBMIT_URL, submit

_PAYLOAD = {
    "url": "https://example-tool.onrender.com",
    "email": "dev@example.com",
    "service_name": "Example Tool",
    "description": "Does a thing.",
    "website_url": "https://example-tool.onrender.com",
    "category": "Data",
    "endpoints": ["/do-the-thing"],
}


@respx.mock
@pytest.mark.asyncio
async def test_success_returns_zero():
    respx.post(SUBMIT_URL).mock(
        return_value=httpx.Response(
            201, json={"data": {"submission_id": "abc-123", "status": "pending"}}
        )
    )
    assert await submit(_PAYLOAD, private_key=None, pay=False) == 0


@respx.mock
@pytest.mark.asyncio
async def test_payment_required_with_no_wallet_is_a_safe_dry_run():
    """The core safety guarantee: no --private-key/--pay means nothing is
    ever paid, even when the API asks for money."""
    respx.post(SUBMIT_URL).mock(
        return_value=httpx.Response(
            402,
            json={
                "x402Version": 2,
                "accepts": [{"amount": "1000000", "network": "eip155:8453"}],
                "error": "free_host_fee_required",
                "message": "Costs $1 because this is a free-compute host.",
            },
        )
    )
    # No private key, no --pay: must return non-zero (not submitted) and must
    # not raise trying to build a paying wallet/transport.
    assert await submit(_PAYLOAD, private_key=None, pay=False) == 1


@respx.mock
@pytest.mark.asyncio
async def test_unexpected_status_is_reported_not_swallowed():
    respx.post(SUBMIT_URL).mock(return_value=httpx.Response(500, text="oops"))
    assert await submit(_PAYLOAD, private_key=None, pay=False) == 1
