#!/usr/bin/env python3
"""Sample autonomous agent client for the Link Preview Cache API.

Same x402 flow as link-preview-api's client. The one thing this script adds:
it calls the SAME url twice, so you can watch "cached": false on the first
call (real fetch, cache populated) and "cached": true on the second (served
from the shared cache) - the actual proof of the product's premise.

Usage:
    python agent_client.py --url https://example.com
    python agent_client.py --url https://example.com --api https://your-deployment.example.com
    python agent_client.py --url https://example.com --private-key 0xabc...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http.clients.httpx import x402_httpx_transport
from x402.mechanisms.evm.exact import ExactEvmScheme

DEFAULT_NETWORK = "eip155:84532"  # Base Sepolia testnet


async def _call_once(http: httpx.AsyncClient, api_base: str, target_url: str) -> dict | None:
    response = await http.get(f"{api_base}/preview", params={"url": target_url})

    payment_response = response.headers.get("payment-response") or response.headers.get(
        "x-payment-response"
    )
    if payment_response:
        print("[agent] Payment settled:")
        print(json.dumps(_decode_header(payment_response), indent=2))

    if response.status_code == 402:
        print("[agent] Still 402 after a payment attempt -- likely insufficient funds.")
        print(response.text)
        return None
    if response.status_code >= 400:
        print(f"[agent] Request failed: {response.status_code}")
        print(response.text)
        return None
    return response.json()


async def run(
    api_base: str,
    target_url: str,
    private_key: str | None,
    network: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    if private_key:
        account = Account.from_key(private_key)
        print(f"[agent] Using wallet: {account.address}")
    else:
        account = Account.create()
        print(f"[agent] No wallet supplied -- generated a throwaway one: {account.address}")
        print(
            "[agent] It holds $0. Fund it with testnet USDC via "
            "https://faucet.circle.com/ (Base Sepolia) to complete real payments."
        )

    client = x402Client()
    client.register(network, ExactEvmScheme(signer=account))

    transport = x402_httpx_transport(client, transport=inner_transport)
    async with httpx.AsyncClient(transport=transport, timeout=30) as http:
        print(f"[agent] Call #1: GET {api_base}/preview?url={target_url}")
        first = await _call_once(http, api_base, target_url)
        if first is None:
            return 1
        print(json.dumps(first, indent=2))
        print(f"[agent] cached={first.get('cached')} (expect False - first time seeing this URL)")

        print(f"\n[agent] Call #2: same URL again, should hit cache and cost less")
        second = await _call_once(http, api_base, target_url)
        if second is None:
            return 1
        print(json.dumps(second, indent=2))
        print(f"[agent] cached={second.get('cached')} (expect True - served from cache)")

        return 0


def _decode_header(value: str) -> object:
    """Payment-Response headers are base64(JSON); fall back to raw text."""
    import base64
    import contextlib

    with contextlib.suppress(Exception):
        return json.loads(base64.b64decode(value))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous agent client for the Link Preview Cache x402 API")
    parser.add_argument("--url", required=True, help="Public URL to fetch a preview for")
    parser.add_argument("--api", default="http://localhost:8000", help="Base URL of the Link Preview Cache API")
    parser.add_argument(
        "--private-key",
        default=None,
        help="Hex private key of the paying wallet (0x...). Generates a throwaway one if omitted.",
    )
    parser.add_argument(
        "--network", default=DEFAULT_NETWORK, help="CAIP-2 network id (default: Base Sepolia testnet)"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run(args.api, args.url, args.private_key, args.network))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
