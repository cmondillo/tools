# Content Moderation API

A pay-per-call API that checks text for profanity/explicit terms and
returns a redacted version — priced and sold entirely through
[x402](https://www.x402.org/): **$0.005 per call, paid in USDC, no
signup, no API key, no human in the loop.** Sold two ways: raw HTTP
(`api/`) and as an MCP tool (`api/app/mcp_server.py`) for coding agents
that speak MCP directly.

```
POST https://your-deployment.example.com/moderate
{"text": "You are a bitch and an asshole."}
```
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

## Why this problem, and why not solved 100 times already

Any agent that publishes text on someone's behalf — a reply, a support
message, generated content — needs a fast first-pass check before it goes
out. The obvious "free" alternatives (Google's Perspective API, most
commercial moderation APIs) all require a human to sign up for an account
and an API key first — exactly the step an autonomous agent can't do on
its own. That's the actual gap x402 is for: not that moderation is hard to
build, but that the free options aren't *actually* free for something
that can't click through a signup form. Paying $0.005 autonomously is
something an agent can do; registering for an API key is not.

## How it works: wordlist matching, not a black box

This is honestly scoped, on purpose: it matches text against the
[LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words)
English word/phrase list (CC BY 4.0 — see `api/app/data/NOTICE.md`), with
word-boundary matching (so "assassin" doesn't get flagged for containing
"ass" — the classic profanity-filter false positive) and detection of
common obfuscation (`@` for `a`, repeated letters like "biiiitch"). It is
**not** a machine-learning toxicity classifier — no context understanding,
no sarcasm detection, no reclaimed-language nuance, and it only catches
terms on the list. That's a deliberate, honest scope: a fast, cheap
first-pass filter, not a replacement for a full moderation pipeline on
high-stakes content. Said plainly here and in the API docs, not buried.

## How it's sold: x402 (same mechanism as `link-preview-api`)

1. Agent calls `POST /moderate` with no payment.
2. Server replies `402 Payment Required` with a signed price quote.
3. The agent's wallet signs a USDC payment authorization locally and
   retries with the payment attached.
4. Server verifies + settles via a **facilitator** (this API never touches
   a private key or an RPC node directly) and returns the result.

## Project layout

```
api/
  app/
    main.py           routes + the x402 middleware wiring
    mcp_server.py      the same product, sold over MCP instead of HTTP
    payment.py          price/network/payee config + Bazaar discovery declaration
    moderation.py        the actual product: wordlist matching, obfuscation detection
    data/
      en_wordlist.txt     403 terms (LDNOOBW, CC BY 4.0)
      NOTICE.md            attribution
  tests/                 20 tests: unit (moderation logic), API-level, MCP-level,
                          and one full mocked-facilitator integration test with
                          real payment signing end to end
  Dockerfile
  .env.example
automation-client/      sample autonomous agent (POST variant of link-preview-api's)
deploy/                 Render + Fly.io configs
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

- `GET /healthz`, `GET /`, `GET /favicon.ico` are free.
- `POST /moderate` is the paid route.
- MCP variant: `python -m app.mcp_server` (needs `CDP_API_KEY_ID`/`CDP_API_KEY_SECRET` set to actually initialize against a real facilitator, same as the HTTP app).

Run the tests: `cd api && pytest` — all 20 run fully offline (facilitator
mocked with respx), including a full end-to-end test with a real (test)
wallet really signing a real EIP-3009 payment authorization against the
real FastAPI app.

## Status

Built, tested (20/20, including the full paid-flow integration test),
**not yet deployed**. Same next steps as `link-preview-api` had: deploy
via `deploy/render.yaml` on Render's free tier, set `X402_PAY_TO_ADDRESS`,
switch to CDP facilitator + Base mainnet when ready for real money — see
`link-preview-api/README.md`'s "Status" section for the detailed walkthrough
of each of those steps; the mechanics are identical here.
