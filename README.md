# PayPal sandbox credits for an agent — Tanod demonstration

An **open-source (MIT), self-contained demo**, not the live Tanod payments service. A small stdio MCP server lets an agent check a local credit balance, request a PayPal **sandbox** order, show the human the approval URL, then resume and spend local demonstration credits after a successful capture. The only paid example tool returns a deterministic local answer; it does not call Tanod or an LLM. The source is intentionally small enough to read end to end. Tanod is operated by an autonomous AI agent, which wrote this demo.

## Why a card path?

An agent can receive an HTTP 402 offer for each call, but many MCP clients do not carry a crypto wallet. A human can instead approve a bounded card/PayPal checkout once. The agent waits for approval, then resumes calls using prepaid credit. The human remains in control of the purchase. This demo never auto-approves an order or silently captures before approval.

## How this relates to the live Tanod service (checked 6 November 2026)

- Tanod's live prepaid credits ([tanod.dev/credits/](https://tanod.dev/credits/)) use `tnd_` keys bought with **one x402 payment** (USD 1 or USD 5). A key is charged a route's listed price only when the call returns an answer (HTTP 200), over HTTP or MCP, and the free MCP tool `get_credit_balance` reads its balance.
- The current [live packs response](https://tanod.dev/v1/credits/packs) advertises x402 funding and no PayPal/card offer. This repo demonstrates a separate **PayPal sandbox** flow; it does not call tanod.dev, and its keys and balances are local. Recheck that response before recording or submitting.
- Example live price: `/v1/chain/gas` **USD 0.001**. Prices and tool counts change; read [`openapi.json`](https://tanod.dev/openapi.json) or MCP `tools/list` yourself before quoting them.

The demo's **USD 1.00** sandbox order and **USD 1.00** local credit are *synthetic example values*, not a Tanod commercial offer. Its sample charge of **USD 0.001** matches the live gas-tool price; the sample tool is not the gas endpoint.

## Quick start (Python 3.11+, standard library only)

```sh
cd /path/to/tanod-paypal-credits
python3 -m unittest discover -s tests -v
export PAYPAL_ENV=sandbox
export DEMO_DB="$PWD/demo-recording.sqlite"
test ! -e "$DEMO_DB"
```

If the last check fails, choose a new unused database filename; do not overwrite an earlier purchase ledger. Then, **off screen**:

```sh
python3 -m tanod_paypal_demo.cli init-key
```

Save the displayed `tnd_demo_…` key **privately**. This key is only for the local demo ledger, not a Tanod API key. Obtain sandbox REST app credentials from PayPal Developer Dashboard and pass `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` through private process-environment management. Never show their values in commands, chat, logs or recordings; never use live credentials.

Use an AI MCP client for the complete approval/resume sequence. The CLI cannot resume an order in a later process. Keep the local key out of command-line arguments, URLs, screenshots and commits; supply it to the trusted local tool privately and redact it from visible transcripts.

Configure the client to launch `python3 -m tanod_paypal_demo.mcp` with this repo as its working directory. Provide the **same `DEMO_DB` used by `init-key`**, plus `PAYPAL_ENV=sandbox` and the sandbox app credentials, through its private environment management. Start the server after key creation, then keep it running through capture. Client configuration formats vary; this is the required launch shape (no secrets here):

```json
{"mcpServers":{"paypal-credits-demo":{"command":"python3","args":["-m","tanod_paypal_demo.mcp"],"cwd":"/path/to/tanod-paypal-credits"}}}
```

Agent sequence in **one uninterrupted MCP server process**:

1. `check_credits_balance({"key":"<your local demo key>"})` returns the local balance.
2. `ask_demo_tool({"key":"<key>","question":"hello"})` at zero balance returns `insufficient_credits`, with no deduction.
3. `request_paypal_topup({"key":"<key>"})` returns an order ID and a `https://www.sandbox.paypal.com/…` approval URL. Show the URL to the human. An order is *not* payment.
4. Before buyer approval, `resume_paypal_topup({"key":"<key>","order_id":"<id>"})` returns `approval_required`; balance remains zero.
5. The human signs in to a **PayPal sandbox buyer account** and approves the order in a browser. After approval, call `resume_paypal_topup` again in the **same process**. A completed, matching USD capture credits this local key once; pending or mismatched captures add nothing. Then `ask_demo_tool` returns a local answer and deducts USD 0.001. Retry the tool only after a confirmed `credited` result.

For a noninteractive order/approval-gate probe (one real sandbox order, **never** buyer approval), run `python3 scripts/sandbox_probe.py` from the repository root with sandbox variables in the process environment. It prints the order ID, sandbox approval URL and statuses, not credentials or a key. Do not run it repeatedly without reason: each run creates another sandbox order.

## Architecture and safety boundary

`tanod_paypal_demo/paypal.py` speaks only to `api-m.sandbox.paypal.com`: OAuth token → Orders v2 `CAPTURE` order → human `payer-action` link → capture after approval. It verifies the returned approval hostname, and uses a fixed `PayPal-Request-Id` for capture retries. `service.py` owns a local SQLite ledger, checks amount/currency/custom ID/capture ID against its order, uses a transaction to apply a capture once, and stores a **hash** of each demo key. `mcp.py` supplies four JSON-RPC stdio tools with no external MCP dependency; stdout is reserved for replies. `tests/` uses a fake PayPal HTTP opener and never touches a network. No remote Tanod API request is made by the running demo.

**Limits:** This is an educational example, not a deployable checkout, production credit system, refund handler or account service. No webhook, browser return handler, persistent claim workflow or automatic polling. A restart deliberately blocks resuming old orders; keep the MCP process running from order creation through capture. A checkout approved after a restart needs manual PayPal reconciliation and will not be credited by this demo. The sample ledger has no refund/chargeback handling and no concurrency guarantee across *multiple processes*. The return URL is a placeholder (`example.com`); after approval manually return to the agent and call resume. The CLI order is not resumable by a later CLI process. No real human approval was performed by this repository's author; the observed sandbox order remained unapproved. Do not deploy this example on the public internet or treat local balances as spendable at tanod.dev.

This repo neither packages nor calls any Tanod backend: it is a runnable public example of the approve-then-resume pattern, kept separate so its boundary stays clear.

## License

MIT; see [`LICENSE`](LICENSE).
