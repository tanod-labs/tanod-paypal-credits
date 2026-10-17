# PayPal sandbox credits for an agent — Tanod demonstration

A **self-contained, MIT-licensed demo**, not the live Tanod payments service. A small stdio MCP server lets an agent check a local credit balance, request a PayPal **sandbox** order, show the human the approval URL, then resume and spend local demonstration credits after a successful capture. The only paid example tool returns a deterministic local answer; it does not call Tanod or an LLM. The source is intentionally small enough to read end to end.

## Why a card path?

An agent can receive an HTTP 402 offer for each call, but many MCP clients do not carry a crypto wallet. A human can instead approve a bounded card/PayPal checkout once. The agent waits for approval, then resumes calls using prepaid credit. The human remains in control of the purchase. This demo never auto-approves an order or silently captures before approval.

## What is live, as checked 18 October 2026

Read directly from [`https://tanod.dev/openapi.json`](https://tanod.dev/openapi.json) and the live `POST https://tanod.dev/mcp` `tools/list` response on that date, **not from an earlier proposal**:

- OpenAPI had **289 paths, 292 operations, 287 operations with `x-tanod-pricing`**. MCP `tools/list` returned **281 tools** and **no credit-balance tool**. These measures have different scopes; they are not a claim that every operation is an MCP tool.
- Published examples of USD prices: `/v1/chain/gas` **0.001**; `/v1/check/address` **0.005**; `/v1/scan/source` **0.25 standard / 0.75 large**; `/v1/scan/package` **0.02 standard / 0.05 large**. Prices and tool counts can change; query the endpoints yourself before filming or quoting them elsewhere.
- The live OpenAPI has **no `/v1/credits/…` path**; `/v1/credits/packs` returned **404**, and an unauthenticated check of `/credits/` returned **403**. The PayPal credit routes are being developed separately and **are not publicly available**; a functional live buyer page was not verified. Do not describe this local demo as a live Tanod integration or advertise a current Tanod PayPal pack price.

The demo's **USD 1.00** sandbox order and **USD 1.00** local credit are *synthetic example values*, not a Tanod commercial offer. Its sample charge of **USD 0.001** uses the gas-tool price read from live OpenAPI on the check date; the sample tool is not the gas endpoint.

## Quick start (Python 3.11+, standard library only)

```sh
cd /path/to/tanod-paypal-credits
python3 -m unittest discover -s tests -v
python3 -m tanod_paypal_demo.cli init-key
```

Save the displayed `tnd_demo_…` key **privately**. This key is only for the local demo ledger, not a Tanod API key. For a PayPal sandbox order, obtain **sandbox REST app** client ID/secret from PayPal Developer Dashboard. Set them in your shell/process environment; never add them to a command line, repository, output file or public recording. For example, use a local ignored file outside this repo with restrictive permissions and source it into the shell; the program reads `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` at runtime. Set `PAYPAL_ENV=sandbox` if desired; any other value is rejected. Never use live credentials here.

```sh
# In the same process environment as the commands below, set your sandbox variables securely.
export PAYPAL_ENV=sandbox
python3 -m tanod_paypal_demo.cli --db /tmp/tanod-demo.sqlite balance --key 'YOUR_LOCAL_DEMO_KEY'
python3 -m tanod_paypal_demo.cli --db /tmp/tanod-demo.sqlite request-topup --key 'YOUR_LOCAL_DEMO_KEY'
```

The CLI creates an order and returns a sandbox PayPal URL but **does not** run a persistent session for resuming; use the MCP server below for the complete approval/resume sequence. `--key` is a demo key; on a shared system, command-line arguments can be visible to other users. For a privacy-sensitive run, use the MCP client instead and store its configuration outside the repository. Never put keys in a URL, logs, screenshots or a commit.

Configure a stdio MCP client to launch `python3 -m tanod_paypal_demo.mcp` with this repo as its working directory and `PAYPAL_ENV=sandbox`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and optional `DEMO_DB=/private/path/credits.sqlite` provided via your client's private environment management. Restart the MCP server once after running `init-key` if it was already open. Example client configuration shape (no secrets here):

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

The separately developed Tanod credit backend in another codebase must be released and verified before a real Tanod PayPal top-up can be demonstrated. Its current design uses real `tnd_` keys and a `/v1/credits/paypal/order` + `/capture` flow, but this repo neither packages nor calls that unpublished backend. This separation keeps a runnable public example honest about its boundary.

## License

MIT; see [`LICENSE`](LICENSE).
