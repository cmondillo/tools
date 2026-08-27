# Marketplace listing — Content Moderation API

Copy-paste ready content for wherever this gets listed. Live at
`https://content-moderation-api-hhy1.onrender.com` (Base Sepolia testnet
pricing until mainnet is switched on — see README.md "Status").

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

**Network:** Base Sepolia testnet currently (`eip155:84532`) — mainnet
switch pending, see README.md "Status"

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

Nothing yet — not deployed. Once live, follow the exact same playbook as
`link-preview-api` (see `/PUBLISHING.md` at the repo root): x402 Bazaar is
automatic via the CDP facilitator pattern already wired into `payment.py`;
`scripts/publish_x402list.py` handles x402-list.com in one command;
x402scan.com and the community GitHub lists are the same few-minutes-manual
steps as before.
