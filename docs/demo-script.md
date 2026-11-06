# Demo video — 2:45, PayPal sandbox

Preparation notes are not narration. Record an actual AI client using the MCP tools, not a staged chat or a mock capture. Use English captions and no music. Hide credentials, local demo keys, buyer identity, browser profile, desktop clock and notifications throughout. Never show payment credentials in a terminal, configuration screen, clipboard or chat.

## Before recording

1. Follow the repository's sandbox setup privately. Use a sandbox REST app and a sandbox personal buyer account. The demo rejects live mode; a real-money purchase is neither necessary nor supported by this demo. No real purchase is authorized by this script. Keep any optional live x402 demonstration separate and label it correctly.
2. On the recording machine, use Python 3.11+ and a clean checkout:

   ```sh
   git clone https://github.com/tanod-labs/tanod-paypal-credits.git
   cd tanod-paypal-credits
   python3 -m unittest discover -s tests -v
   ```

3. Configure the sandbox app's `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` through private process-environment management, **off screen**. Do not type their values into commands or paste them into an AI chat. Use one fresh local ledger for key creation and the MCP server:

   ```sh
   export PAYPAL_ENV=sandbox
   export DEMO_DB="$PWD/demo-recording.sqlite"
   test ! -e "$DEMO_DB"
   ```

   If the check fails, choose a new unused filename; do not overwrite an earlier purchase ledger. Then, off screen:

   ```sh
   python3 -m tanod_paypal_demo.cli init-key
   ```

   Save the displayed local demo key privately. It is not a live Tanod key.
4. Configure a trusted AI MCP client to run this server with the repository as its working directory. Use its private environment settings to pass the same `DEMO_DB` and sandbox app variables. Clients differ in configuration format; this is the required launch shape, not a universal config-file location:

   ```json
   {"mcpServers":{"paypal-credits-demo":{"command":"python3","args":["-m","tanod_paypal_demo.mcp"],"cwd":"/absolute/path/to/tanod-paypal-credits"}}}
   ```

   The launched command is `python3 -m tanod_paypal_demo.mcp`. Start it once after key creation. **Keep that process running through approval and capture.** Do not restart the client, open another server or use separate CLI requests to resume an order.
5. Supply only the local demo key to the trusted local tool/client, off screen. The tool schema requires it; redact it from every visible call, response and chat transcript. Tell the AI client:

   > Use the PayPal sandbox MCP tools below with my local demo key. Never reveal the key. Pause before creating an order and before capture so I can confirm each step. Do not approve purchases yourself, retry an uncertain purchase, or claim success from an approval link. Quote actual tool results only.

   Check the recording preview before starting. Do not use a client that exposes app credentials to the model.

## Shot list and narration

| Time | Exact screen/action | Narration or caption |
|---|---|---|
| 0:00–0:10 | Title over the public repository README/license. | “Pay-per-call tools for AI agents, funded with PayPal. Open source (MIT), operated by an autonomous AI agent. PayPal sandbox demonstration.” |
| 0:10–0:25 | Browser: `https://tanod.dev/credits/`, then `https://tanod.dev/v1/credits/packs`. Do not show a private balance. | “Live Tanod credits currently advertise x402 funding. This separate sandbox example shows a human-approved PayPal path. Its local credit cannot be spent on the live service.” |
| 0:25–0:35 | Terminal: rerun `python3 -m unittest discover -s tests -v`; show the actual result. | “Six offline tests check the ledger and payment states using a fake PayPal transport. The checkout next uses the real sandbox API.” |
| 0:35–0:55 | AI client: call balance, then sample tool, using calls A and B below. Show the actual zero balance and `insufficient_credits`. | “The AI agent has no credit. The sample tool refuses and deducts nothing.” |
| 0:55–1:15 | AI client: authorize call C once. Show the returned sandbox approval URL and USD 1.00 example amount. | “The agent requests credit. PayPal creates a sandbox order; creating an order is not payment.” |
| 1:15–1:30 | AI client: authorize call D before approval, then A. Show `approval_required` and unchanged balance. | “Before human approval, no credit is added.” |
| 1:30–1:55 | Browser: open the returned `https://www.sandbox.paypal.com/…` URL, review USD 1.00 and approve as the sandbox buyer. Sign-in is off screen or fully redacted. | “A human reviews and approves one dollar of test money in PayPal sandbox. No real funds move.” |
| 1:55–2:15 | Return manually from the placeholder return page to the same AI client. Authorize D; only if it returns `credited`, ask for D again. | “The server captures and validates the payment. This completed capture adds local credit once. Repeating resume reports already credited.” |
| 2:15–2:35 | AI client: B, then A. Show `answered`, charge USD 0.001 and remaining USD 0.999, only if actually returned. | “The AI agent resumes. This deterministic local sample costs one thousandth of a dollar in demo credit. It is not an AI-generated answer or a hosted Tanod call.” |
| 2:35–2:45 | Public repository URL and MIT license. | “PayPal sandbox calls, local demo credits, human approval. Open source (MIT): github.com/tanod-labs/tanod-paypal-credits.” |

Cuts may remove waiting or sign-in, never replace a result or imply an unperformed capture. Runtime target 2:45; keep the complete upload under 3:00.

## Exact tool calls

These are **tool names and arguments**, not shell commands. Ask the AI client to make them. Replace placeholders privately; never display the actual key. The order ID is the one returned by C, not a fabricated example.

A — `check_credits_balance`

```json
{"key":"<LOCAL_DEMO_KEY>"}
```

B — `ask_demo_tool`

```json
{"key":"<LOCAL_DEMO_KEY>","question":"hello"}
```

C — `request_paypal_topup`

```json
{"key":"<LOCAL_DEMO_KEY>"}
```

D — `resume_paypal_topup`

```json
{"key":"<LOCAL_DEMO_KEY>","order_id":"<ORDER_ID_FROM_C>"}
```

Expected sequence, not claimed recording evidence: A `0.00`; B `insufficient_credits`; C approval URL; D `approval_required`; A `0.00`; buyer approval; D `credited`/`1.00`; D `already_credited`/`1.00`; B `answered`/`0.001`/`0.999`; A `0.999`. Live `get_credit_balance` is a different tool; do not substitute it for the local demo's `check_credits_balance`.

## Failure and submission rules

- If approval, capture or crediting fails, stop. Keep the order ID privately for reconciliation; do not create another order to mask an unresolved result. Never swap in mocked-test output for the buyer checkout.
- `pending`, `held_for_review`, a timeout or a restart is not success. The restarted demo cannot resume the old order. Record an honest diagnostic if useful, but do not submit it as an end-to-end success video; resolve the missing step first.
- Open the official [event](https://paypalaihackathon.devpost.com/) and [rules](https://paypalaihackathon.devpost.com/rules) in a browser before upload. Direct server requests returned 403; confirm current length, visibility, AI and judge-access requirements. Search-index rules specify **publicly visible YouTube**, not merely unlisted.
- Review the whole exported video for private details and truthful continuity. Upload it publicly on YouTube, under three minutes, then paste that URL into Devpost. Confirm all current rules and submit before the event's displayed deadline.
