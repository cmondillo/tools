# automation-client

Same idea as `link-preview-api/automation-client`: a minimal, honest example
of an autonomous agent paying for and consuming this API, no human in the
loop, POST instead of GET this time.

```
pip install -r requirements.txt
python agent_client.py --text "You are a jerk." --api http://localhost:8000
```

Run it with no `--private-key` and it generates a throwaway wallet with $0
in it - you'll see the negotiation happen and then fail at "insufficient
funds", which is expected and still proves the handshake works. To see a
real paid call end to end:

1. Get a Base Sepolia (testnet) wallet - any EVM wallet works.
2. Fund it with testnet USDC from https://faucet.circle.com/.
3. `python agent_client.py --text "..." --api <your API URL> --private-key 0x...`
