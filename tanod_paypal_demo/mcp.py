"""A tiny stdio MCP server for the local sandbox credit demonstration.

No third-party SDK required. One JSON-RPC line in, one line out. The four tools
expose a local balance, a human approval link, a guarded resume, and a sample call.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .paypal import PayPalError
from .service import Demo, DemoError

TOOLS = [
    {"name": "check_credits_balance", "description": "Check the local demo balance, not a live Tanod balance.",
     "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
    {"name": "request_paypal_topup", "description": "Create a PayPal SANDBOX order and return its approval URL for a human. Does not charge or add credits.",
     "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
    {"name": "resume_paypal_topup", "description": "After the human approves the sandbox order, capture it and fund the local demo key once.",
     "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}, "order_id": {"type": "string"}},
                     "required": ["key", "order_id"]}},
    {"name": "ask_demo_tool", "description": "Local deterministic example: consumes $0.001 demo credit only on an answer. Not a live Tanod tool.",
     "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}, "question": {"type": "string"}},
                     "required": ["key", "question"]}},
]
CALLS = {"check_credits_balance": ("balance", ("key",)),
         "request_paypal_topup": ("request_topup", ("key",)),
         "resume_paypal_topup": ("resume_topup", ("key", "order_id")),
         "ask_demo_tool": ("demo_answer", ("key", "question"))}


def dispatch(demo: Demo, message: dict) -> dict | None:
    method, mid = message.get("method"), message.get("id")
    if not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32600, "message": "Invalid request"}}
    if mid is None:  # notifications have no reply
        return None
    if method == "initialize":
        result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "tanod-paypal-sandbox-demo", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params")
        name = params.get("name") if isinstance(params, dict) else None
        args = params.get("arguments", {}) if isinstance(params, dict) else None
        if name not in CALLS or not isinstance(args, dict):
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}
        function, required = CALLS[name]
        if any(not isinstance(args.get(key), str) for key in required):
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "Missing or invalid string arguments"}}
        try:
            output = getattr(demo, function)(**{key: args[key] for key in required})
            result = {"content": [{"type": "text", "text": json.dumps(output)}], "isError": False}
        except (DemoError, PayPalError, ValueError) as exc:
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> int:
    # A private local file only. Point DEMO_DB to an empty directory you control.
    db_path = Path(os.environ.get("DEMO_DB", str(Path.home() / ".local/share/tanod-paypal-demo/credits.sqlite")))
    demo = Demo(db_path)
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                reply = dispatch(demo, request) if isinstance(request, dict) else {
                    "jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
            except (ValueError, UnicodeError):
                reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            if reply is not None:
                print(json.dumps(reply, separators=(",", ":")), flush=True)
    finally:
        demo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
