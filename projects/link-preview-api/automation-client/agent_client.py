#!/usr/bin/env python3
"""Sample autonomous agent client for the Link Preview API.

Demonstrates the full agent workflow against an x402-gated API with ZERO
human intervention at call time:

  1. Agent calls the API.
  2. Server responds 402 Payment Required with a signed price quote.
  3. Agent's wallet signs a USDC payment authorization (EIP-3009) locally.
  4. Agent retries the request with the payment attached.
  5. Server verifies + settles the payment via its facilitator, then returns data.

All of that (steps 2-5) happens inside the httpx transport below — the
calling code just does a normal `await http.get(...)`.

Usage:
    python agent_client.py --url https://example.com
    python agent_client.py --url https://example.com --api https://your-deployment.example.com
    python agent_client.py --url https://example.com --private-key 0xabc...

If no --private-key is given, a fresh throwaway testnet wallet is generated
on the spot. That wallet holds $0, so the payment itself will fail with
"insufficient funds" -- which is expected, and still proves the discovery
and negotiation handshake works end-to-end. Fund it with testnet USDC via
https://faucet.circle.com/ (pick Base Sepolia) to see a real paid call.
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


async def run(
    api_base: str,
    target_url: str,
    private_key: str | None,
    network: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    """Run one paid request. `inner_transport` is a seam for tests (e.g. an
    ASGI transport pointed at an in-process app) — real usage leaves it
    unset and talks over the network."""
    if private_key:
        account = Account.from_key(private_key)
        print(f"[agent] Using wallet: {account.address}")
    else:
        account = Account.create()
        print(f"[agent] No wallet supplied -- generated a throwaway one: {account.address}")
        print(
            "[agent] It holds $0. Fund it with testnet USDC via "
            "https://faucet.circle.com/ (Base Sepolia) to complete a real payment."
        )

    client = x402Client()
    client.register(network, ExactEvmScheme(signer=account))

    transport = x402_httpx_transport(client, transport=inner_transport)
    async with httpx.AsyncClient(transport=transport, timeout=30) as http:
        print(f"[agent] GET {api_base}/preview?url={target_url}")
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
            return 1

        if response.status_code >= 400:
            print(f"[agent] Request failed: {response.status_code}")
            print(response.text)
            return 1

        print("[agent] Result:")
        print(json.dumps(response.json(), indent=2))
        return 0


def _decode_header(value: str) -> object:
    """Payment-Response headers are base64(JSON); fall back to raw text."""
    import base64
    import contextlib

    with contextlib.suppress(Exception):
        return json.loads(base64.b64decode(value))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous agent client for the Link Preview x402 API")
    parser.add_argument("--url", required=True, help="Public URL to fetch a preview for")
    parser.add_argument("--api", default="http://localhost:8000", help="Base URL of the Link Preview API")
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
