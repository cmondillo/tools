#!/usr/bin/env python3
"""Submit any project in this portfolio to x402-list.com's real, documented,
versioned public API (POST /api/v1/submit) - not a scraped/private endpoint.

Safe by default: never spends money unless you explicitly pass both
--private-key and --pay. Without them, a submission that requires payment
(free-compute-host penalty, or a resubmission fee) prints exactly what it
would cost and stops - a genuine dry run, not a simulation.

Usage:
    python scripts/publish_x402list.py \\
        --url https://my-new-tool.onrender.com \\
        --email you@example.com \\
        --name "My New Tool" \\
        --description "What it does, one sentence." \\
        --category Data \\
        --endpoint /do-the-thing

    # once you've seen the dry-run quote and want to actually pay it:
    python scripts/publish_x402list.py ... --private-key 0x... --pay

Valid --category values: AI, Blockchain, Compute, Content, Data, Finance,
Other, Verification (from x402-list.com's own /categories endpoint).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx

SUBMIT_URL = "https://x402-list.com/api/v1/submit"
PAY_NETWORK = "eip155:8453"  # Base mainnet - matches x402-list.com's own pricing


def build_payload(args: argparse.Namespace) -> dict:
    payload = {
        "url": args.url,
        "email": args.email,
        "service_name": args.name,
        "description": args.description,
        "website_url": args.website or args.url,
        "category": args.category,
        "endpoints": args.endpoint,
    }
    if args.notes:
        payload["notes"] = args.notes
    return payload


def _build_transport(private_key: str):
    # Imported lazily: these come from the x402 SDK's eth/httpx extras, which
    # a caller who never intends to pay shouldn't need installed just to run
    # a dry run.
    from eth_account import Account
    from x402 import x402Client
    from x402.http.clients.httpx import x402_httpx_transport
    from x402.mechanisms.evm.exact import ExactEvmScheme

    account = Account.from_key(private_key)
    client = x402Client()
    client.register(PAY_NETWORK, ExactEvmScheme(signer=account))
    print(f"[publish] Paying wallet: {account.address}")
    return x402_httpx_transport(client)


async def submit(payload: dict, *, private_key: str | None, pay: bool) -> int:
    transport = _build_transport(private_key) if (private_key and pay) else None

    async with httpx.AsyncClient(transport=transport, timeout=30) as http:
        response = await http.post(SUBMIT_URL, json=payload)

        if response.status_code in (200, 201):
            print("[publish] Submitted:")
            print(json.dumps(response.json(), indent=2))
            return 0

        if response.status_code == 402:
            body = response.json()
            quote = body.get("accepts", [{}])[0]
            amount_atomic = quote.get("amount")
            amount_usd = int(amount_atomic) / 1_000_000 if amount_atomic else None
            print(
                f"[publish] Payment required"
                + (f": ${amount_usd:.2f} USDC" if amount_usd is not None else "")
            )
            print("[publish] Reason:", body.get("message") or body.get("error") or "(none given)")
            if transport is None:
                print(
                    "[publish] Dry run - no --private-key/--pay given, nothing was paid. "
                    "Re-run with both to actually submit and pay."
                )
            else:
                print(
                    "[publish] Payment was attempted automatically and still came back 402 - "
                    "check the wallet's USDC balance on Base and try again."
                )
            return 1

        print(f"[publish] Unexpected response: {response.status_code}")
        print(response.text)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Base URL of the x402 service")
    parser.add_argument("--email", required=True, help="Contact email for review correspondence")
    parser.add_argument("--name", required=True, dest="name", help="Human-readable service name")
    parser.add_argument("--description", required=True, help="One-sentence description")
    parser.add_argument("--category", required=True,
                         choices=["AI", "Blockchain", "Compute", "Content", "Data", "Finance", "Other", "Verification"])
    parser.add_argument("--endpoint", action="append", required=True, dest="endpoint",
                         help="Paid endpoint path to probe, e.g. /preview. Repeatable.")
    parser.add_argument("--website", default=None, help="Public website/repo URL (defaults to --url)")
    parser.add_argument("--notes", default=None)
    parser.add_argument("--private-key", default=None, help="Hex private key of the paying wallet (0x...)")
    parser.add_argument("--pay", action="store_true",
                         help="Actually authorize spending, if a payment is required. Without this, "
                              "a required payment is only reported, never sent.")
    args = parser.parse_args()

    payload = build_payload(args)
    print("[publish] Submitting:")
    print(json.dumps(payload, indent=2))
    sys.exit(asyncio.run(submit(payload, private_key=args.private_key, pay=args.pay)))


if __name__ == "__main__":
    main()
