# Publishing playbook

How every tool in this portfolio gets in front of agents, and exactly how
much of that is actually automatic. Written after doing it for real once
(`link-preview-api`) and learning precisely where automation does and
doesn't hold up — not a plan, a record of what worked.

## The channels, honestly ranked by how automatic they really are

### 1. x402 Bazaar (Coinbase's official index) — fully automatic, zero effort

Not a publishing step at all. It's a property of how the API is built:
switch its facilitator to CDP (`CDP_API_KEY_ID`/`CDP_API_KEY_SECRET`, see
each project's `app/config.py` and `app/payment.py`) and declare a Bazaar
discovery extension on the paid route (`declare_discovery_extension(...)`
in `app/payment.py`). Every future project that copies this pattern is
Bazaar-listed the moment it's deployed on mainnet. Nothing to run, nothing
to remember.

Docs: https://docs.cdp.coinbase.com/x402/bazaar · public directory:
Agentic.Market. (Don't confuse either with `x402bazaar.org` — a broken,
unrelated third-party site with its own bugs, not Coinbase's.)

### 2. x402-list.com — scripted, one real command

`x402-list.com` has a genuine, documented, versioned public REST API
(`https://x402-list.com/api`, OpenAPI spec at `/openapi.json`). That's worth
automating against, and `scripts/publish_x402list.py` does:

```
python scripts/publish_x402list.py \
    --url https://your-new-tool.onrender.com \
    --email you@example.com \
    --name "Your New Tool" \
    --description "One sentence." \
    --category Data \
    --endpoint /your-paid-path
```

Safe by default — it never spends money. If the API asks for a fee (a free
compute host like Render/Fly/Railway triggers a one-time $1, non-refundable,
per their rules), the script prints exactly what it would cost and stops.
Only re-running with `--private-key 0x... --pay` actually authorizes and
sends that payment. Tested against the real API shape in
`scripts/test_publish_x402list.py` (mocked, no network/money needed to run
the tests).

### 3. x402scan.com — manual, and deliberately left that way

x402scan's "Add API" button isn't backed by a documented public API — it's
an internal call inside their Next.js app (tRPC), not meant for third-party
programmatic use. Scraping it would be a fragile hack pretending to be
automation, not real automation. It's also genuinely fast by hand: open
`https://www.x402scan.com/resources/register`, paste the URL, click "Add
API." A few seconds, no wallet, no signature. Just do it each time.

### 4. MCP Registry (`registry.modelcontextprotocol.io`) — mostly scripted, one manual login per machine

The official MCP server directory (replaced the old README-list-of-links
approach in `modelcontextprotocol/servers`). Requires the tool's MCP server
to be reachable over the network, not just runnable as a local stdio
process - see `app/mcp_server.py`'s `streamable_http_path="/"` +
`transport_security` handling and `main.py`'s `/mcp` mount in
`link-preview-api`/`content-moderation-api` for the pattern. Each project
gets its own `server.json` at its root (`io.github.cmondillo/<slug>`
namespace, `remotes` pointing at `<deployment-url>/mcp`).

Publishing itself:

```
mcp-publisher validate   # from the project's own folder, next to server.json
mcp-publisher login github   # one-time per machine - opens a device-code flow, needs a browser
mcp-publisher publish
```

`validate` and `publish` are ordinary HTTP calls and can run from anywhere
(including this session, which is how `server.json` gets checked before
committing). `login` is the one step that can't be automated end-to-end: it's
a generic GitHub OAuth device-code flow, not a repo-scoped git operation, so
this session's GitHub proxy rejects it outright - it has to run from a
real machine with a browser, once, and the resulting credential is reusable
for future publishes/updates from that machine.

### 5. Community "awesome list" GitHub PRs — manual by design, not by limitation

`xpaysh/awesome-x402` and `Merit-Systems/awesome-agentic-commerce` both took
a real PR (#1343 and #630 for `link-preview-api`). This one stays a light
manual step on purpose, for two reasons:

- A PR is a public action attributed to your GitHub identity. Silently
  opening PRs against other people's repos every time a new tool ships,
  without you ever seeing the diff first, crosses from automation into
  something you'd rather approve.
- The tooling that did this (forking + pushing + opening the PR) only works
  once a fork already exists under your account and is attached to the
  session — the first click (GitHub's own "Edit this file," which auto-forks)
  has to happen in a browser once per list.

The repeatable version of this, each time there's a new tool: I find the
right insertion point and exact format in the target list's README (this
is genuinely fast now that the drill is known), hand you the exact line and
a minimal click sequence, and verify the PR landed once you're done. Budget
about two minutes per list per tool, not a research project.

## Adding a new tool to all of this

1. Build it following the same pattern as `link-preview-api` (see its
   `app/payment.py` for the Bazaar-discoverable, CDP-facilitator wiring).
2. Deploy it, verify it's live (root `/`, `/healthz`, and a real 402 on the
   paid route).
3. Run `scripts/publish_x402list.py` for that tool's details.
4. Two-minute manual step on x402scan.com.
5. Mount MCP at `/mcp` (see `content-moderation-api/api/app/main.py` for the
   pattern), add a `server.json`, `mcp-publisher validate`, then a one-time
   `mcp-publisher login github` + `publish` from a real machine.
6. Ask for the awesome-list PRs — same repos as before, same format, just a
   new entry.

## Security note

`scripts/publish_x402list.py` takes a private key only via `--private-key`
on the command line, only when you explicitly pass `--pay`, and only holds
it in memory for that one process — it's never written to a file or logged.
Treat that flag exactly like you'd treat pasting a password: don't do it in
a place anyone else can see your terminal or shell history.
