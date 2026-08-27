# automation-client

A minimal, honest example of an **autonomous agent** consuming the Link
Preview API: no human clicks anything, no API key is exchanged in advance.
The agent's wallet signs a payment on the spot when the server asks for one.

```
pip install -r requirements.txt
python agent_client.py --url https://example.com --api http://localhost:8000
```

What happens:

1. The client sends a plain `GET /preview?url=...`.
2. The server replies `402 Payment Required` with a signed price quote
   (asset, amount, network, payee).
3. `x402_httpx_transport` intercepts that 402, has the wallet sign a USDC
   payment authorization locally, and retries the same request with the
   payment attached — all inside the one `await http.get(...)` call.
4. The server verifies and settles the payment via its facilitator, then
   returns the metadata.

Run it with no `--private-key` and it generates a throwaway wallet with $0
in it — you'll see the negotiation happen and then fail at "insufficient
funds", which is expected and still proves steps 1-3 work. To see a real
paid call end to end:

1. Get a Base Sepolia (testnet) wallet — any EVM wallet works.
2. Fund it with testnet USDC from https://faucet.circle.com/.
3. `python agent_client.py --url https://example.com --api <your API URL> --private-key 0x...`
