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

## Projects

| Project | What it sells | Status |
|---|---|---|
| [`link-preview-api`](projects/link-preview-api/) | Pay-per-call URL metadata (Open Graph/title/description/image) extraction | **Live on Base mainnet, earning real USDC**: https://link-preview-api-z4nf.onrender.com |

## Repo conventions

- Every project is fully self-contained in `projects/<project-slug>/`: its
  own code, tests, Dockerfile, deploy config, and README. Nothing is shared
  between projects and nothing project-specific lives at the repo root.
- Every project ships with:
  - `api/` — the paid service itself
  - `automation-client/` — a sample agent that pays for and consumes it
  - `deploy/` — ready-to-use deploy configs (Render/Fly/etc.)
  - `README.md` — the business case, architecture, and exact steps to take
    it from "runs on my machine" to "earning money"
  - `LISTING.md` — the marketplace/directory listing copy, ready to publish
- New projects get added the same way: a clean new folder, same skeleton,
  linked in the table above.
