# Marketplace listing — Content Moderation API

Copy-paste ready content for wherever this gets listed. Live at
`https://content-moderation-api-hhy1.onrender.com` on Base mainnet — real
USDC.

## Listing copy

**Name:** Content Moderation API

**One-liner:** Check text for profanity/explicit terms, get a redacted
version back. $0.005 per call, paid in USDC, no signup.

**Description:**
> Wordlist-based profanity/explicit-content detection with basic
> obfuscation handling (leetspeak, repeated letters). Returns a flag,
> the matched terms, and a redacted version of the text. Built for agents
> that publish text on someone's behalf and need a fast first-pass check
> before it goes out — priced and paid entirely over the x402 protocol,
> so an agent can pay for it autonomously instead of needing a human to
> sign up for an API key first (which most "free" moderation APIs still
> require). Honestly scoped: pattern/wordlist matching, not a machine-
> learning classifier — no context or sarcasm understanding, only catches
> terms on its list. Sold over both raw HTTP and MCP.

**Endpoint:** `POST https://content-moderation-api-hhy1.onrender.com/moderate` — body `{"text": "..."}`

**Price:** $0.005 USD per successful call, settled in USDC

**Network:** Base mainnet (`eip155:8453`)

**Protocol:** [x402](https://www.x402.org/) — HTTP 402 Payment Required,
also available as an MCP tool (`moderate_text`)

**Category / tags:** `moderation`, `profanity-filter`, `content-safety`, `agents`

**Example request:**
```
POST https://content-moderation-api-hhy1.onrender.com/moderate
Content-Type: application/json

{"text": "You are a bitch and an asshole."}
```

**Example response:**
```json
{
  "flagged": true,
  "matches": [
    {"term": "bitch", "start": 10, "end": 15},
    {"term": "asshole", "start": 23, "end": 30}
  ],
  "match_count": 2,
  "redacted_text": "You are a ***** and an *******."
}
```

**Docs:** `https://content-moderation-api-hhy1.onrender.com/docs` (auto-generated OpenAPI/Swagger UI)

**Source:** this repository

## Listed so far

- **x402-list.com** — submitted, status `pending` (awaiting review/probe).
  Submission ID `72bd602f-b1b5-4e74-b3d8-e397745a8df7`. Paid the $1
  free-host submission fee autonomously via [Poncho](https://tryponcho.com/)
  (tx `0xaa99039128cf3363b80465a9fcc2e6f4ec00966683caabfe7e4b01abb5587a01`
  on Base) — a genuine third-party agent paying a genuine third-party
  service to list this API, no manual clicking on either end.
- **x402scan.com** — listed and confirmed correct:
  https://www.x402scan.com/server/ad47f50a-62d1-4400-bf43-99517852cb0e.
  Name, icon, description, wallet address, and all 4 resources (`GET /`,
  `/favicon.ico`, `/healthz`, `POST /moderate` priced `<$0.01`) all show
  up right. Test call made and confirmed working correctly (flagged
  "bullshit", left milder words like "hell"/"damn"/"crap" alone —
  matches the wordlist's deliberately conservative scope). The
  Activity panel (Transactions/Volume/Buyers) still reads 0 — that's a
  separate indexer that lags real settlements, same as observed with
  `link-preview-api` early on; not a problem with the listing or the
  API.
- **x402 Bazaar (CDP auto-index)** — should be automatic since we're on
  the CDP facilitator; not independently verified.
- **GitHub awesome-lists** — PRs open on both:
  - [xpaysh/awesome-x402 #1344](https://github.com/xpaysh/awesome-x402/pull/1344) —
    open, no conflicts, awaiting maintainer merge.
  - [Merit-Systems/awesome-agentic-commerce #631](https://github.com/Merit-Systems/awesome-agentic-commerce/pull/631) —
    open, blocked on a required reviewer approval (repo rule, not
    something we can do ourselves).
