"""Local demonstration ledger and guarded PayPal sandbox top-up workflow.

This ledger is intentionally NOT Tanod's production credit store. It only funds the
local sample tool. The claim stays in the MCP process, never in tool output or a URL.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import threading
from decimal import Decimal
from pathlib import Path

from .paypal import PayPalError, PayPalSandbox

PACK = "1"  # A sandbox-only $1 demonstration purchase, not an advertised Tanod pack.
PRICE = Decimal("1.00")
CREDIT = 1_000_000  # The local demo credits $1; not the upstream card-pack offer.
DEMO_CALL = 1_000  # $0.001, verified against the live gas-tool OpenAPI price on 2026-10-18.
KEY_RE = re.compile(r"^tnd_demo_[A-Za-z0-9_-]{43}$")
ORDER_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")


class DemoError(Exception):
    """An expected failure safe to show to an MCP caller."""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def usd(value: int) -> str:
    return format(Decimal(value) / 1_000_000, ".3f" if value % 10_000 else ".2f")


class Demo:
    def __init__(self, db_path: Path, paypal: PayPalSandbox | None = None):
        self.path = Path(db_path).expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise DemoError("Database must not be a symlink")
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        if os.name == "posix":
            os.chmod(self.path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout = 5000")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts(key_hash TEXT PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS orders(
                id TEXT PRIMARY KEY, account TEXT NOT NULL, pack TEXT NOT NULL,
                state TEXT NOT NULL, capture_id TEXT,
                FOREIGN KEY(account) REFERENCES accounts(key_hash));
        """)
        self.paypal = paypal
        self._lock = threading.RLock()
        self._session_orders: set[str] = set()

    def close(self):
        self.db.close()

    def create_key(self) -> str:
        key = "tnd_demo_" + secrets.token_urlsafe(32)
        with self._lock:
            self.db.execute("INSERT INTO accounts(key_hash,balance) VALUES (?,0)", (_hash(key),))
        return key

    def _account(self, key: str) -> str:
        if not KEY_RE.fullmatch(key):
            raise DemoError("A valid local demo key is required (run init-key first)")
        digest = _hash(key)
        if not self.db.execute("SELECT 1 FROM accounts WHERE key_hash=?", (digest,)).fetchone():
            raise DemoError("Unknown local demo key")
        return digest

    def balance(self, key: str) -> dict:
        with self._lock:
            account = self._account(key)
            row = self.db.execute("SELECT balance FROM accounts WHERE key_hash=?", (account,)).fetchone()
            return {"balance_usd": usd(row[0]), "source": "local demo ledger (not a Tanod account)"}

    def _paypal(self) -> PayPalSandbox:
        if self.paypal is None:
            self.paypal = PayPalSandbox.from_env()
        return self.paypal

    def request_topup(self, key: str) -> dict:
        with self._lock:
            account = self._account(key)  # refuse bad key before calling PayPal
            # No web callback runs here: buyer approves on PayPal; agent resumes this same process.
            order = self._paypal().create_order(pack=PACK, price_usd=str(PRICE),
                return_url="https://example.com/tanod-demo-approved",
                cancel_url="https://example.com/tanod-demo-cancelled")
            if not ORDER_RE.fullmatch(order.order_id):
                raise DemoError("PayPal returned an invalid order ID")
            self.db.execute("INSERT INTO orders(id,account,pack,state) VALUES (?,?,?,?)",
                            (order.order_id, account, PACK, "created"))
            self._session_orders.add(order.order_id)
            return {"order_id": order.order_id, "approval_url": order.approve_url,
                    "sandbox_price_usd": str(PRICE), "demo_credit_usd": usd(CREDIT),
                    "next_step": "Ask the human to approve on PayPal sandbox. Then call resume_topup with this order ID in this same MCP session. Do not claim payment is complete yet."}

    def resume_topup(self, key: str, order_id: str) -> dict:
        if not ORDER_RE.fullmatch(order_id):
            raise DemoError("Invalid order ID")
        with self._lock:
            account = self._account(key)
            row = self.db.execute("SELECT * FROM orders WHERE id=? AND account=?", (order_id, account)).fetchone()
            # The order must belong to this local key and have been created by this process.
            if row is None or order_id not in self._session_orders:
                raise DemoError("Unknown order in this MCP session; a restarted process cannot resume an old order")
            if row["state"] == "credited":
                return {"status": "already_credited", **self.balance(key)}
            capture = self._paypal().capture(order_id)
            if capture.status == "not_approved":
                return {"status": "approval_required", "message": "Human approval on the sandbox PayPal page is required; no credit was added."}
            if capture.status == "pending":
                return {"status": "pending", "message": "PayPal has not completed the capture; retry later. No credit was added."}
            if capture.status != "completed":
                return {"status": "declined", "message": "PayPal did not complete this order; no credit was added."}
            if (capture.amount != PRICE or capture.currency != "USD" or
                    capture.custom_id != f"tanod-demo-credits-{PACK}" or not capture.capture_id):
                self.db.execute("UPDATE orders SET state='review' WHERE id=?", (order_id,))
                return {"status": "held_for_review", "message": "Capture did not match the order; no credit was added."}
            self.db.execute("BEGIN IMMEDIATE")
            try:
                state = self.db.execute("SELECT state FROM orders WHERE id=?", (order_id,)).fetchone()[0]
                if state != "created":
                    self.db.execute("ROLLBACK")
                    return {"status": "already_credited" if state == "credited" else "held_for_review", **self.balance(key)}
                self.db.execute("UPDATE orders SET state='credited', capture_id=? WHERE id=?",
                                (capture.capture_id, order_id))
                self.db.execute("UPDATE accounts SET balance=balance+? WHERE key_hash=?", (CREDIT, account))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            return {"status": "credited", **self.balance(key)}

    def demo_answer(self, key: str, question: str) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise DemoError("Provide a nonempty question of at most 500 characters; no credit was charged")
        with self._lock:
            account = self._account(key)
            self.db.execute("BEGIN IMMEDIATE")
            try:
                changed = self.db.execute("UPDATE accounts SET balance=balance-? WHERE key_hash=? AND balance>=?",
                                          (DEMO_CALL, account, DEMO_CALL)).rowcount
                if not changed:
                    self.db.execute("ROLLBACK")
                    return {"status": "insufficient_credits", "price_usd": usd(DEMO_CALL), **self.balance(key),
                            "next_step": "Call request_topup and ask a human to approve; retry this tool after resume_topup credits the account."}
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            return {"status": "answered", "answer": "Local demonstration answer: " + question.strip(),
                    "charged_usd": usd(DEMO_CALL), **self.balance(key),
                    "disclaimer": "This is a deterministic local example, not a live Tanod tool or an AI-generated answer."}
