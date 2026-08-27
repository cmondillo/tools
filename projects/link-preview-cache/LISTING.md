# Marketplace listing — Link Preview Cache API

Copy-paste ready content for wherever this gets listed. Live at
`https://link-preview-cache-api.onrender.com` on Base mainnet — real USDC.

## Listing copy

**Name:** Link Preview Cache API

**One-liner:** Same link preview data as link-preview-api, at roughly a
third of the price — served from a shared cache.

**Description:**
> Given a public URL, returns its Open Graph / meta metadata: title,
> description, preview image, favicon, canonical URL. Same product as
> `link-preview-api`, same x402 protocol, but backed by a shared TTL cache
> - most requests are served from cache instead of a fresh fetch, which is
> what makes $0.003/call (vs. the usual $0.01) sustainable rather than a
> loss-leader. `/cache-stats` is free and public, so the caching claim is
> checkable, not just asserted. Also available as an MCP tool.

**Endpoint:** `GET https://link-preview-cache-api.onrender.com/preview?url=<public http(s) URL>`

**Price:** $0.003 USD per successful call, settled in USDC

**Network:** Base mainnet (`eip155:8453`)

**Protocol:** [x402](https://www.x402.org/) — HTTP 402 Payment Required,
also available as an MCP tool (`preview_url`)

**Category / tags:** `link-preview`, `metadata`, `web`, `scraping`, `cache`, `agents`

**Docs:** `https://link-preview-cache-api.onrender.com/docs`

**Source:** this repository

## Listed so far

Not yet submitted anywhere — live on mainnet, but no directory
submissions done yet. Once ready, follow the same playbook as
`content-moderation-api` (`../PUBLISHING.md`): x402scan, x402-list.com,
MCP Registry, GitHub awesome-lists.
