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

- **MCP Registry** — `server.json` written and schema-validated
  (`io.github.cmondillo/link-preview-cache-api`, remote streamable-HTTP at
  `/mcp`). Not published yet - needs `mcp-publisher publish` from a real
  machine (device-code GitHub login already done for the other two
  projects, so just the publish command this time).
- **GitHub awesome-lists** — branches pushed, PRs not yet opened (needs
  the two-click submit from the compare links, same as before):
  - `xpaysh/awesome-x402`: https://github.com/xpaysh/awesome-x402/compare/main...cmondillo:awesome-x402:add-link-preview-cache-api
  - `Merit-Systems/awesome-agentic-commerce`: https://github.com/Merit-Systems/awesome-agentic-commerce/compare/master...cmondillo:awesome-agentic-commerce:add-link-preview-cache-api
- **x402-list.com** — not submitted yet. Costs $1 USDC (free-host fee,
  same as `content-moderation-api`); needs Poncho or similar to pay it.
- **x402scan.com** — not submitted yet. Visit
  https://www.x402scan.com/resources/register and paste the URL (a few
  seconds, no wallet).
- **x402 Bazaar (CDP auto-index)** — should be automatic since we're on
  the CDP facilitator; not independently verified.
