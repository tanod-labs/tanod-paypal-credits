"""Local demo CLI. Never prints sandbox credentials or a purchase claim."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .paypal import PayPalError
from .service import Demo, DemoError


def main(argv=None):
    p = argparse.ArgumentParser(description="PayPal SANDBOX + local agent-credits demo")
    p.add_argument("--db", default=os.environ.get("DEMO_DB", str(Path.home() / ".local/share/tanod-paypal-demo/credits.sqlite")))
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("init-key", help="create a local demo key (printed once)")
    for name in ("balance", "request-topup", "ask"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--key", required=True, help="local demo key")
        if name == "ask":
            cmd.add_argument("--question", required=True)
    args = p.parse_args(argv)
    demo = Demo(Path(args.db))
    try:
        if args.action == "init-key":
            result = {"key": demo.create_key(), "warning": "Local demo key only. Keep private; never commit or paste into public logs."}
        elif args.action == "balance":
            result = demo.balance(args.key)
        elif args.action == "request-topup":
            result = demo.request_topup(args.key)
        else:
            result = demo.demo_answer(args.key, args.question)
        print(json.dumps(result))
        return 0
    except (DemoError, PayPalError, ValueError) as exc:
        p.exit(1, f"Error: {exc}\n")
    finally:
        demo.close()


if __name__ == "__main__":
    raise SystemExit(main())
