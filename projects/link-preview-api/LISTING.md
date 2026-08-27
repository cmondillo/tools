# Marketplace listing — Link Preview API

Copy-paste ready content for wherever this gets listed. Live at
`https://link-preview-api-z4nf.onrender.com` (Base Sepolia testnet pricing
until mainnet is switched on — see README §"Status").

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
