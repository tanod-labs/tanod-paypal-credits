# Demo script — 2:35 target, English, no music

**Production note:** Record the real screen only. Blur demo keys and sandbox buyer identifiers. Captions are English. Do not show or narrate the post-approval segment until a human has actually completed sandbox approval and the tool has returned `credited`. If approval cannot be completed, end with the truthful pre-approval result and say the remainder requires a sandbox buyer.

| Time | Shot | Voice and on-screen caption |
| --- | --- | --- |
| 0:00–0:18 | Title and architecture sketch: agent → local MCP credits tool → PayPal sandbox approval → local demo tool. | “Agents often meet a per-call price without a wallet. This prototype gives a human a clear PayPal approval step before local prepaid use.” Caption: **PayPal sandbox / local demonstration; not live Tanod checkout**. |
| 0:18–0:38 | Show live OpenAPI price for `/v1/chain/gas`; switch to README source note. | “We checked live pricing before this recording; the example price was USD 0.001 on 18 October 2026. This repo’s answer tool is a local simulation, not that endpoint.” Caption: **Verify the current price before recording.** |
| 0:38–0:56 | Terminal: offline tests passing; then MCP tools/list and zero `check_credits_balance` result, with key redacted. | “Four small MCP tools implement a balance check, sandbox order, resume, and deterministic sample call. Offline tests mock PayPal.” Caption: **Local balance: USD 0.00**. |
| 0:56–1:13 | Call `ask_demo_tool`, insufficient credits. | “The agent cannot spend credit it does not have, so no answer is charged.” Caption: **Insufficient balance; no deduction**. |
| 1:13–1:35 | Call `request_paypal_topup`, display sanitized order ID and sandbox approval URL; pause visibly before capture. | “An order is not a payment. The agent hands the sandbox approval link to the human.” Caption: **Human approval required**. |
| 1:35–1:53 | Call `resume_paypal_topup` before approving: `approval_required`; show unchanged balance. | “Capture is refused before buyer approval, and the local ledger remains at zero.” Caption: **No approval → no credit**. |
| 1:53–2:20 | **Only after a real human sandbox-buyer approval**: record PayPal sandbox approval screen without personal information, then call resume in the same MCP session. | “The human approves in PayPal sandbox; the agent resumes. We verify the completed USD capture matches the order before crediting exactly once.” Caption: **Completed matching sandbox capture → local demo credit**. |
| 2:20–2:35 | **Only if capture succeeded**: call local answer tool and balance; otherwise show README limits and end. | “The demo tool now answers and deducts its sample price. Production Tanod checkout is a separate backend pending release.” Caption: **Local example only; live integration not yet released**. |

Editing rule: if no sandbox buyer has approved, cut at 1:53 and use a 20-second honest limits outro. Do not recreate or fake a successful capture. Upload/publication and the actual submission are separate steps outside this repository.
