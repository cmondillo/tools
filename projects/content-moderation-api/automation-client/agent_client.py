#!/usr/bin/env python3
"""Sample autonomous agent client for the Content Moderation API.

Same idea as link-preview-api's agent_client.py, adapted for a POST+JSON
endpoint instead of GET+query-param. See that file for the full explanation
of what's happening; this one keeps the comments short.

Usage:
    python agent_client.py --text "You are a jerk."
    python agent_client.py --text "..." --api https://your-deployment.example.com
    python agent_client.py --text "..." --private-key 0xabc...

No --private-key generates a throwaway wallet (holds $0 - proves the
negotiation handshake, not a real payment). Fund it via
https://faucet.circle.com/ (Base Sepolia) for a real paid call.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
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
    text: str,
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
            "https://faucet.circle.com/ (Base Sepolia) to complete a real payment."
        )

    client = x402Client()
    client.register(network, ExactEvmScheme(signer=account))

    transport = x402_httpx_transport(client, transport=inner_transport)
    async with httpx.AsyncClient(transport=transport, timeout=30) as http:
        print(f"[agent] POST {api_base}/moderate  {{'text': {text!r}}}")
        response = await http.post(f"{api_base}/moderate", json={"text": text})

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
    with contextlib.suppress(Exception):
        return json.loads(base64.b64decode(value))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous agent client for the Content Moderation x402 API")
    parser.add_argument("--text", required=True, help="Text to check")
    parser.add_argument("--api", default="http://localhost:8000", help="Base URL of the Content Moderation API")
    parser.add_argument("--private-key", default=None, help="Hex private key of the paying wallet (0x...)")
    parser.add_argument("--network", default=DEFAULT_NETWORK, help="CAIP-2 network id (default: Base Sepolia testnet)")
    args = parser.parse_args()

    exit_code = asyncio.run(run(args.api, args.text, args.private_key, args.network))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
