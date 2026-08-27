# Link Preview Cache API

A pay-per-call link preview API — same data as `link-preview-api`, same
[x402](https://www.x402.org/) protocol — but at roughly **a third of the
price** ($0.003 vs $0.01), because most requests are served from a shared
cache instead of a fresh fetch every time. This is a first instance of a
pattern that doesn't exist yet in the x402 ecosystem: a caching layer for
idempotent, agent-facing paid APIs. Every mature API ecosystem eventually
gets one (CDNs, Redis-fronted APIs, HTTP caching) — pay-per-call agent APIs
haven't, yet.

```
GET https://your-deployment.example.com/preview?url=https://example.com/blog/post
```
```json
{
  "url": "https://example.com/blog/post",
  "title": "Example Post Title",
  "description": "A short description of the page.",
  "image": "https://example.com/og-image.png",
  "cached": true
}
```

## Why caching, and why it's sustainable, not just a loss-leader discount

x402 quotes a price *before* the handler runs, so a per-request "cheaper
if it's a cache hit" price isn't really an option (it would need to know
the outcome before charging for it). Instead: **one flat price, always**,
made sustainable because most incoming requests cost *us* almost nothing
to serve — see `potential/simulate_savings.py` for the actual model, not
just an assertion. Its headline numbers, at a realistic Zipf-skewed
request pattern (some URLs get looked up a lot, most rarely — the standard
long-tail shape for shared web content):

| Requests/day | Cache hit rate | Our real fetches | Agent savings vs. $0.01/call |
|---:|---:|---:|---:|
| 100 | 26% | 74 | 70% |
| 1,000 | 58% | 421 | 70% |
| 10,000 | 79% | 2,153 | 70% |
| 100,000 | 94% | 6,080 | 70% |

Agents save a flat 70% either way (same price regardless of hit/miss), but
notice what happens to *our* side: at 100k requests/day, we do real work on
only ~6% of them. That gap is the whole business case — it's what funds the
lower price, and it gets *more* favorable as traffic grows, not less. That's
the flywheel: more agents using it → higher hit rate → more room to cut the
price further or widen margin, either way the product gets more attractive
with scale instead of less. Run `python potential/simulate_savings.py`
yourself — every assumption (pool size, skew, TTL, prices) is a constant at
the top of the file, change any of them and re-run.

**Honest scoping:** cache keys are exact URL strings, unnormalized — two
URLs that are "the same page" but differ in a trailing slash or query
param order won't share a cache hit. Stated plainly here rather than
implying smarter canonicalization than actually exists.

## Manually seeding the cache

Some sites (Coinbase, Dexscreener, and others) return `403` to any
scraper — there's no legitimate way for `preview.py`'s fetch to ever
populate them, no matter how well-behaved it is. `POST/GET/DELETE
/admin/cache` lets the operator insert, inspect, or remove an entry by
hand instead, so a paying agent asking about one of those URLs still gets
a real answer:

```
POST /admin/cache
Authorization: Bearer <ADMIN_TOKEN>
{"url": "https://coinbase.com", "title": "Coinbase", "description": "..."}
```

Not x402 - protected by a fixed bearer token (`ADMIN_TOKEN` env var,
unset by default, which disables these routes entirely - a 503, not an
open door). Hidden from `/docs`; not part of the public product surface.
See `.env.example` for how to set one.

## How it's sold: x402 (same mechanism as the other two projects)

1. Agent calls `GET /preview?url=...` with no payment.
2. Server replies `402 Payment Required` with a signed price quote.
3. The agent's wallet signs a USDC payment authorization locally and
   retries with the payment attached.
4. Server checks its cache first (`app/cache.py`, SQLite, TTL-bound). Hit:
   returns instantly, `"cached": true`. Miss: fetches + parses for real
   (SSRF-hardened, same approach as `link-preview-api`), caches the result,
   returns it with `"cached": false`.
5. Payment verifies + settles via a facilitator either way, same price.

Also sold over MCP, mounted on this same deployment at `POST /mcp`
(streamable HTTP) — see `content-moderation-api`/`link-preview-api` for
why this pattern beats stdio-only.

## Project layout

```
api/
  app/
    main.py           routes + the x402 middleware wiring + the MCP mount
    mcp_server.py      the same product, sold over MCP
    payment.py          price/network/payee config + Bazaar discovery declaration
    preview.py            fetch + parse a URL (SSRF-hardened; ported, not imported
                           cross-project, per this repo's self-containment convention)
    cache.py               the actual product idea: SQLite TTL cache in front of preview.py
  tests/                 40 tests: cache logic, manual admin/cache seeding,
                          preview parsing/SSRF, payment config, API-level,
                          MCP-level, and one full mocked-facilitator
                          integration test that proves the second call for
                          the same URL hits cache (not a second fetch)
  Dockerfile
  .env.example
automation-client/      sample agent that calls the SAME url twice, showing
                        cached:false then cached:true
deploy/                 Render + Fly.io configs
potential/
  simulate_savings.py   the savings/hit-rate model behind the numbers above
docker-compose.yml
```

## Run it locally

```
cd api
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- `GET /healthz`, `GET /`, `GET /favicon.ico`, `GET /cache-stats` are free.
  `/cache-stats` is deliberately unpaid and public — it's the receipts for
  the "cheaper because of caching" claim, so anyone should be able to check
  the cache is actually being used, not just take the pricing on faith.
- `GET /preview?url=...` is the paid route.
- MCP: `POST /mcp` on this same app, or standalone: `python -m app.mcp_server`.

Run the tests: `cd api && pytest` — all 40 run fully offline (facilitator
mocked with respx), including the full end-to-end test with a real (test)
wallet really signing a real EIP-3009 payment authorization, that also
proves the origin site gets fetched exactly once across two calls for the
same URL.

Try the savings model: `cd potential && python simulate_savings.py`.

## Status

1. **Build it.** Done — tested, working locally, same pattern as the other
   two projects.
2. ~~Deploy it somewhere public.~~ **Done.** Live on Render's free tier:
   **https://link-preview-cache-api.onrender.com**
3. ~~Switch to mainnet.~~ **Done.** `X402_NETWORK=eip155:8453`, CDP
   facilitator. Verified live: `GET /preview` shows a real Base mainnet
   USDC payment page (no Sepolia/testnet mention).
4. **Get it in front of agents.** See `LISTING.md` and the repo-root
   `PUBLISHING.md` playbook — not done yet for this project.

Live on **Base mainnet today** — real money, same as the other two
projects. Own CDP API key (a fresh one, created during this project's
setup) rather than the shared one `link-preview-api`/`content-moderation-api`
use — no functional difference, both work identically against the CDP
facilitator.
