# Demo video script (2:45, English captions, sandbox only, no music)

Record the real screen only; never fake a step. Before recording: set the sandbox variables privately (not on screen),
use a fresh `DEMO_DB` file, clear the terminal history, hide the desktop, clock, browser profile and account names.
Blur every `tnd_demo_` key and the sandbox buyer email. Voice-over is optional; captions carry the script. Drive the
tools from an MCP client with a chat agent (best), or type the JSON-RPC lines into `python3 -m tanod_paypal_demo.mcp`
in one terminal. Keep ONE server process running from step 4 to step 8.

| # | Time | Shot | Caption / narration |
|---|---|---|---|
| 1 | 0:00-0:12 | Title card | "Pay-per-call tools for AI agents, funded with PayPal. PayPal sandbox. Open source (MIT). Built and operated by an autonomous AI agent." |
| 2 | 0:12-0:32 | Browser: tanod.dev/credits/ | "Tanod sells tools to AI agents, paid per call, only when a call answers. Prepaid credits are bought with x402 today, and many agent users have no crypto wallet." |
| 3 | 0:32-0:45 | Terminal: the 6 offline tests pass; `init-key` (key blurred) | "This repo adds a PayPal path. Six offline tests; no dependencies." |
| 4 | 0:45-1:05 | Agent: list tools; check balance (0.00); call `ask_demo_tool` | "The agent has no credit. The paid tool refuses and charges nothing." |
| 5 | 1:05-1:22 | Agent: `request_paypal_topup` returns order ID and sandbox approval link | "The agent asks for a top-up. An order is not a payment: a human must approve it." |
| 6 | 1:22-1:35 | Agent: `resume_paypal_topup` before approval: `approval_required`, balance 0.00 | "No approval, no credit." |
| 7 | 1:35-2:00 | Browser: open the link, sign in as the sandbox personal buyer (email blurred), approve USD 1.00 | "The human reviews and approves USD 1 in PayPal sandbox." |
| 8 | 2:00-2:20 | Agent: resume: `credited`, balance 1.00; resume again: `already_credited` | "The server captures, checks amount and currency, and credits exactly once." |
| 9 | 2:20-2:35 | Agent: `ask_demo_tool`: answer, charged 0.001, balance 0.999 | "The agent carries on, paying per call from its balance." |
| 10 | 2:35-2:45 | Repo URL card | "Sandbox prototype; live Tanod credits use x402 today. Code: github.com/tanod-labs/tanod-paypal-credits" |

If approval or capture fails on the day: stop after shot 6, then close with shot 10 plus the caption "Buyer approval
not shown". Never edit in a capture that did not happen.
