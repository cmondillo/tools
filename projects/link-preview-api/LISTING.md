# Marketplace listing — Link Preview API

Copy-paste ready content for wherever this gets listed. Live at
`https://link-preview-api-z4nf.onrender.com` on Base mainnet — real USDC.

## Where this actually gets listed, and how

x402-gated APIs don't have one central "app store" the way human SaaS does
yet — discovery happens in a few concrete places, in this order:

1. **[x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar)** — the
   closest thing to an official index. If the API's facilitator is
   Coinbase's CDP facilitator (see README §"Status"), the `/preview` route
   is indexed **automatically** the moment it's deployed, because it
   already declares a discovery schema (`app/payment.py`) — nothing to
   submit by hand. Browsable at the Bazaar's own site, and queryable
   directly by any agent via the CDP facilitator's discovery API (no CDP
   key required to *query* it).
2. **[x402-list.com](https://x402-list.com/)** and similar community
   directories — third-party, agent-first directories of x402 services.
   These take a manual submission (name, description, endpoint URL,
   price). The copy below is ready to paste into one.
3. **This repo's own README** — the honest, permanent listing. Anyone
   (human or agent crawling GitHub) landing here sees exactly what it does
   and what it costs.

There is deliberately no listing here on RapidAPI-style human marketplaces:
they assume a human signs up for an API key and gets billed monthly, which
is the opposite of the point of this project.

## Listed so far

- **[x402scan.com](https://www.x402scan.com/server/4f84a447-770a-454c-835d-8392e9b4e8c4)**
  — done, confirmed live (not just submitted): all 4 resources correctly
  indexed, `/`, `/favicon.ico`, `/healthz` correctly marked Public (free)
  and `/preview` correctly priced at $0.01, favicon rendering, network
  `eip155:8453`, wallet address correct, "v2" protocol badge. Free, no
  wallet, no review queue.
- **[`xpaysh/awesome-x402`](https://github.com/xpaysh/awesome-x402)** —
  submitted as [PR #1343](https://github.com/xpaysh/awesome-x402/pull/1343),
  status: open, awaiting maintainer merge. Free, no wallet needed.
- **[`Merit-Systems/awesome-agentic-commerce`](https://github.com/Merit-Systems/awesome-agentic-commerce)**
  (published under the name `awesome-x402`) — submitted as
  [PR #630](https://github.com/Merit-Systems/awesome-agentic-commerce/pull/630),
  status: open, awaiting maintainer merge.
- **x402 Bazaar (CDP auto-index)** — should be automatic since we're on the
  CDP facilitator; not independently confirmed (every domain to check it is
  blocked in the dev sandbox this project was built in — verify from a
  normal browser). Docs: https://docs.cdp.coinbase.com/x402/bazaar — public
  directory: Agentic.Market.
- **x402-list.com** — not submitted. Would cost a one-time $1 USDC because
  the API is hosted on a free-tier host (onrender.com is on their listed
  free-host set); revisit if/when off the free tier. Automated and ready
  to go whenever: `scripts/publish_x402list.py` at the repo root (see
  `PUBLISHING.md`).
- **x402bazaar.org manual listing** — attempted, blocked by a signature bug
  on their own site (their platform-created wallet fails to sign even its
  own listing flow); not something fixable from our side. Not the same
  thing as Coinbase's actual Bazaar (above) — a separate, unrelated,
  broken third-party site.
- **x402Studio / x402layer.cc** — evaluated, deliberately skipped. It's a
  payment-collecting *proxy*: it wants to sit in front of an unprotected
  origin and handle x402 itself, which conflicts with this API already
  having its own CDP-facilitator payment gate (pointing it at the live
  paid endpoint would double-charge / break, since the proxy forwards
  requests unpaid and our own gate would then reject them). Also a
  brand-new platform with no track record, unlike the channels above. To
  revisit: would need a second, API-key-protected *unpaid* variant of the
  endpoint built specifically for their proxy to call (Origin Protection
  toggle in their UI) — real engineering work, not just a form fill.

## Listing copy

**Name:** Link Preview API

**One-liner:** Turn any URL into clean title/description/image metadata.
$0.01 per call, paid in USDC, no signup.

**Description:**
> Given a public URL, returns its Open Graph / meta metadata: title,
> description, preview image, favicon, canonical URL, and site name.
> Built for AI agents that browse, summarize, or share links and need to
> know what a URL actually is without running their own HTML fetcher and
> parser. Priced and paid entirely over the x402 protocol — no API key, no
> account, no monthly bill. An agent calls the endpoint, receives a 402
> price quote, pays $0.01 in USDC, and gets its answer in the same round
> trip.

**Endpoint:** `GET https://link-preview-api-z4nf.onrender.com/preview?url=<public http(s) URL>`

**Price:** $0.01 USD per successful call, settled in USDC

**Network:** Base mainnet (`eip155:8453`)

**Protocol:** [x402](https://www.x402.org/) — HTTP 402 Payment Required

**Category / tags:** `link-preview`, `metadata`, `web`, `scraping`, `agents`

**Example request:**
```
GET https://link-preview-api-z4nf.onrender.com/preview?url=https://example.com/blog/post
```

**Example response:**
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

**Docs:** `https://link-preview-api-z4nf.onrender.com/docs` (auto-generated OpenAPI/Swagger UI)

**Source:** this repository
