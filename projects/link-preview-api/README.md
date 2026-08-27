# Link Preview API

A pay-per-call API that fetches a URL and returns clean metadata (title,
description, image, favicon, canonical link) — the same data your chat app
uses to render a nice link card. Priced and sold entirely through the
[x402](https://www.x402.org/) protocol: **$0.01 per call, paid in USDC,
with no signup, no API key, and no human in the loop.**

```
GET https://your-deployment.example.com/preview?url=https://example.com/blog/post
```

```json
{
  "url": "https://example.com/blog/post",
  "final_url": "https://example.com/blog/post",
  "title": "Example Post Title",
  "description": "A short description of the page.",
  "image": "https://example.com/og-image.png",
  "favicon": "https://example.com/favicon.ico",
  "site_name": "Example",
  "canonical_url": "https://example.com/blog/post",
  "content_type": "text/html; charset=utf-8"
}
```

## Why this problem

Any agent that browses the web, summarizes links, builds a reading list, or
composes a message containing a URL needs to know what that URL actually
*is* before it can do something useful with it — without downloading and
parsing arbitrary HTML itself (which means running an HTTP client with
SSRF protection, an HTML parser, and OG/Twitter-card fallback logic). That's
a small, well-defined, constantly-recurring job — exactly the kind of thing
worth buying by the call instead of building in-house.

## How it's sold: x402

1. Agent calls `GET /preview?url=...` with no payment.
2. Server replies `402 Payment Required` with a signed price quote (asset,
   amount, network, payee) in the `Payment-Required` header.
3. The agent's wallet signs a USDC payment authorization locally (no
   pre-registration, no OAuth) and retries the same request with the
   payment attached.
4. Server verifies + settles the payment through a **facilitator** (a
   third-party service that talks to the chain so this API never touches
   an RPC node or holds custody of anything) and returns the data.

This API never sees a private key and never needs a merchant account —
verification/settlement is delegated entirely to the facilitator. The only
thing it needs to get paid is a wallet address.

It's also **discoverable by agents automatically**: `/preview` declares an
[x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar) discovery schema
(see `app/payment.py`), so a facilitator that indexes the Bazaar — the CDP
facilitator does this by default — can list it without anyone submitting a
form.

## Project layout

```
api/                   the paid service (FastAPI)
  app/
    main.py             routes + the x402 middleware wiring
    payment.py           price/network/payee config + Bazaar discovery declaration
    preview.py            the actual product: fetch a URL, parse its metadata (SSRF-hardened)
    config.py            all settings, read from env vars
  tests/                 16 tests: unit, API-level, and one full mocked-facilitator
                          integration test that exercises real payment signing end to end
  Dockerfile
  .env.example           every setting, documented
automation-client/     a sample autonomous agent that discovers, pays for,
                        and consumes this API — see its own README
deploy/                 ready-to-use configs for Render and Fly.io
docker-compose.yml      local dev
```

## Run it locally

```
cd api
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- `GET /healthz` and `GET /` are free — no payment required.
- `GET /preview?url=...` is the paid route. Hitting it with no payment
  returns `402` with a price quote; see `automation-client/` for a client
  that pays it automatically.

Run the tests:

```
cd api
pytest
```

All 16 tests run fully offline (the facilitator's HTTP calls are mocked
with [respx](https://lundberg.github.io/respx/)) — including one that runs
the *actual* sample agent against the *actual* FastAPI app over an in-process
ASGI transport, with a real (test) wallet really signing a real EIP-3009
payment authorization. That's the strongest guarantee in this repo that the
two sides of the protocol actually agree with each other.

## Status: what's real vs. what's left to flip on

Everything above is built, tested, and — as far as code can prove it —
correct: price quoting, asset resolution (it resolves the real Base Sepolia
USDC contract address and correctly turns `$0.01` into `10000` atomic
units), the Bazaar discovery declaration, SSRF-hardened fetching, and a
full mocked round trip of the payment handshake.

What turns this from a demo into something that earns money — **and is
deliberately left to you, since it involves money and accounts I can't
create on your behalf:**

1. **A real payout wallet.** Set `X402_PAY_TO_ADDRESS` in `api/.env` (or
   your host's env vars) to a Base-compatible address you control. Right
   now it defaults to the Ethereum burn address, so nothing is wired to
   anyone by default.
2. **Deploy it somewhere public.** `deploy/render.yaml` and `deploy/fly.toml`
   are ready to use — pick one, connect your account, deploy. Any Docker
   host works via `api/Dockerfile`.
3. **Switch to mainnet when ready.** `X402_NETWORK=eip155:8453` and a
   mainnet-capable facilitator (the default `https://x402.org/facilitator`
   is testnet-only; for mainnet + automatic Bazaar listing, use
   [Coinbase's CDP facilitator](https://docs.cdp.coinbase.com/x402/core-concepts/facilitator),
   which needs a free CDP account and API key).
4. **Get it in front of agents.** See `LISTING.md` for the ready-to-paste
   listing copy and exactly where it goes.

Until (1)-(3) are done, the API runs correctly against **Base Sepolia
testnet** (fake money, safe to leave on) — that's the default, and it's
what every test in this repo exercises.

## Note on this environment

This project was built inside a sandboxed remote container whose network
egress proxy blocks `x402.org` outright (confirmed via direct requests
during development — not a guess). That means a live call to `/preview` in
*this exact sandbox* returns a clean `503` (see the "facilitator
unreachable" handling in `app/main.py`) rather than a real `402`/paid
response — this is a property of this container's network policy, not of
the code. The full protocol was still proven correct here, twice: once
against the FastAPI test client with the facilitator's responses mocked
(`tests/test_api.py`), and once completely end-to-end with a real wallet
really signing a real payment (`tests/test_integration_agent_flow.py`).
Deployed anywhere with normal internet access — Render, Fly, your laptop —
`/preview` talks to the real facilitator with no code changes.
