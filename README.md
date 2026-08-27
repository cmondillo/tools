# tools

A portfolio of small, single-purpose paid services sold **directly to AI agents** —
no human checkout flow, no dashboard login, no subscription. An agent calls the
API, gets an `HTTP 402 Payment Required` quote, pays a few cents in USDC, and
gets its answer. Fully automatic on both sides.

Each service lives in its own self-contained folder under [`projects/`](projects/)
and follows the same pattern:

- **One narrow problem, solved well.** No platforms, no suites — a single job
  an agent needs done.
- **[x402](https://www.x402.org/)** for payment. HTTP-native, stablecoin
  micropayments, no merchant account or KYC required on the seller side —
  just a wallet address. This is the emerging standard for agent-to-API
  payments (backed by Coinbase, adopted by AWS Bedrock AgentCore, Cloudflare,
  and others as of 2026).
- **Discoverable by agents**, not just humans — each API declares an
  [x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar) discovery schema
  so agents can find and call it without a human ever reading the docs.
- A **sample automation client** included with every project, showing an
  agent discovering, paying for, and consuming the service end-to-end.
- Where it adds real reach, also sold as an **MCP tool**
  (`api/app/mcp_server.py`) — the same product, the same price, a second
  interface for coding agents that discover tools over MCP rather than
  raw HTTP.

## Projects

| Project | What it sells | Status |
|---|---|---|
| [`link-preview-api`](projects/link-preview-api/) | Pay-per-call URL metadata (Open Graph/title/description/image) extraction | **Live on Base mainnet, earning real USDC**: https://link-preview-api-z4nf.onrender.com |
| [`content-moderation-api`](projects/content-moderation-api/) | Pay-per-call profanity/explicit-content detection with redaction, sold over both HTTP and MCP | **Live on Base mainnet, earning real USDC**: https://content-moderation-api-hhy1.onrender.com |
| [`link-preview-cache-api`](projects/link-preview-cache/) | Same product as `link-preview-api`, ~⅓ the price — backed by a shared cache. First instance of a general "x402 cache" pattern | **Live on Base mainnet, earning real USDC**: https://link-preview-cache-api.onrender.com |

## Repo conventions

- Every project is fully self-contained in `projects/<project-slug>/`: its
  own code, tests, Dockerfile, deploy config, and README. Nothing
  product-specific is shared between projects.
- Every project ships with:
  - `api/` — the paid service itself
  - `automation-client/` — a sample agent that pays for and consumes it
  - `deploy/` — ready-to-use deploy configs (Render/Fly/etc.)
  - `README.md` — the business case, architecture, and exact steps to take
    it from "runs on my machine" to "earning money"
  - `LISTING.md` — the marketplace/directory listing copy, ready to publish
- New projects get added the same way: a clean new folder, same skeleton,
  linked in the table above.
- One deliberate exception to "nothing shared": [`scripts/`](scripts/) holds
  portfolio-level *publishing* tooling — not product code, reused across
  every project the same way (e.g. submitting a new tool to x402-list.com's
  API). See [`PUBLISHING.md`](PUBLISHING.md) for the full playbook: what's
  genuinely automatic, what's scripted, and what stays a deliberate manual
  step and why.
