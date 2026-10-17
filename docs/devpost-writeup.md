# Draft Devpost submission text — verify before posting

**Project title:** PayPal sandbox credits for agent tools

**Inspiration**

Agents can reach a tool's price without a payment method. Many MCP clients have no crypto wallet. We wanted a pattern where an agent can ask for a top-up, a human can make an explicit PayPal decision, and the agent can continue only after payment is confirmed.

**What it does**

This open-source Python demonstration runs a local stdio MCP server with four tools: check a local credit balance; create a PayPal sandbox Orders v2 purchase and return the human approval URL; resume after approval to capture and credit exactly once; and consume a small local credit for a deterministic sample answer. It refuses to credit before PayPal approval and checks a completed capture's USD amount, currency and custom ID before adding credit. It is not a checkout on the live Tanod service and does not issue a live Tanod key. Its USD 1 sandbox example is not a Tanod commercial pack.

**How we built it**

Python 3.11 standard library only: urllib HTTPS calls to PayPal sandbox OAuth and Orders v2, SQLite for the local demonstration ledger, JSON-RPC over stdio for MCP, and offline unit/integration tests with a fake PayPal HTTP opener. The approval link is returned for the human; it is not treated as completed payment. Capture retries use a stable PayPal request ID, and the local ledger applies a successful matching capture once. On 18 October 2026, live `https://tanod.dev/openapi.json` exposed the gas price as USD 0.001; our sample tool uses that figure while returning a clearly labeled *local* response. The live MCP `tools/list` then contained 281 tools, none of them a credit-balance tool. The live credits routes were not deployed.

**Challenges**

The important boundary is order creation versus human approval versus completed capture. A created order leaves local balance at zero; the real sandbox probe produced a valid approval URL and a pre-approval `approval_required` response, not a paid result. We also kept credentials out of source, errors and output, and separated the example ledger from an unreleased production credit system. This example intentionally does not reconcile orders across a process restart or handle refunds and chargebacks.

**What's next**

A human-approved sandbox capture and resumed MCP tool call remain to be demonstrated. A later integration could replace the local sample tool with the separately developed Tanod credit backend after release and end-to-end verification. Persistent secure claim recovery, webhook/reconciliation handling and refunds would be required before production use. As built today, this is a sandbox-only prototype, **not a working hosted Tanod PayPal checkout**.
