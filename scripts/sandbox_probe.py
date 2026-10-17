"""Make one real PayPal SANDBOX order, then show that capture needs a buyer.

Run with PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in the *process environment*.
No keys, OAuth tokens, or local demo keys are printed. No live PayPal calls.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from tanod_paypal_demo.paypal import PayPalError
from tanod_paypal_demo.service import Demo


def main():
    if os.getenv("PAYPAL_ENV", "sandbox") != "sandbox":
        raise SystemExit("Refusing non-sandbox mode")
    with tempfile.TemporaryDirectory(prefix="tanod-paypal-sandbox-") as path:
        demo = Demo(Path(path) / "demo.sqlite")
        try:
            key = demo.create_key()
            order = demo.request_topup(key)
            print(json.dumps({"step": "order_created", "order_id": order["order_id"],
                              "approval_url": order["approval_url"], "balance_usd": demo.balance(key)["balance_usd"]}))
            result = demo.resume_topup(key, order["order_id"])
            print(json.dumps({"step": "capture_before_human_approval", **result,
                              "balance_usd": demo.balance(key)["balance_usd"]}))
            return 0 if result["status"] == "approval_required" else 2
        finally:
            demo.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PayPalError as exc:
        sys.exit(f"Sandbox API error: {exc}")
