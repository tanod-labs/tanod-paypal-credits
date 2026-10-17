"""Offline integration tests: real demo ledger + mocked PayPal Orders v2 HTTP."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from tanod_paypal_demo.mcp import dispatch
from tanod_paypal_demo.paypal import PayPalSandbox, PayPalError, approval_url
from tanod_paypal_demo.service import Demo


class Reply:
    def __init__(self, status, body):
        self.status = status
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self, size=-1):
        return self.body[:size]


class FakePayPal:
    def __init__(self):
        self.requests = []
        self.approved = False
        self.mode = "completed"
        self.value = "1.00"
        self.currency = "USD"
        self.custom = "tanod-demo-credits-1"

    def open(self, request, timeout):
        self.requests.append(request)
        path = request.full_url.split("paypal.com", 1)[-1]
        if path == "/v1/oauth2/token":
            assert request.get_header("Authorization", "").startswith("Basic ")
            return Reply(200, {"access_token": "mock-token"})
        assert request.get_header("Authorization") == "Bearer mock-token"
        if path == "/v2/checkout/orders":
            body = json.loads(request.data)
            assert body["intent"] == "CAPTURE"
            assert body["purchase_units"][0]["amount"] == {"currency_code": "USD", "value": "1.00"}
            return Reply(201, {"id": "ORDER123", "status": "PAYER_ACTION_REQUIRED", "links": [
                {"rel": "payer-action", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER123"}]})
        if path.endswith("/capture"):
            assert request.get_header("Paypal-request-id") == "tanod-demo-capture-ORDER123"
            if not self.approved:
                raise urllib.error.HTTPError(request.full_url, 422, "unapproved", {},
                                             io.BytesIO(json.dumps({"details": [{"issue": "ORDER_NOT_APPROVED"}]}).encode()))
            if self.mode == "pending":
                return Reply(201, self.capture_body("PENDING"))
            if self.mode == "already":
                raise urllib.error.HTTPError(request.full_url, 422, "already", {},
                                             io.BytesIO(json.dumps({"details": [{"issue": "ORDER_ALREADY_CAPTURED"}]}).encode()))
            return Reply(201, self.capture_body("COMPLETED"))
        if path == "/v2/checkout/orders/ORDER123":
            return Reply(200, self.capture_body("COMPLETED"))
        raise AssertionError(path)

    def capture_body(self, status):
        return {"id": "ORDER123", "status": "COMPLETED", "purchase_units": [
            {"custom_id": self.custom, "payments": {"captures": [{"id": "CAP123", "status": status,
             "amount": {"currency_code": self.currency, "value": self.value}}]}}]}


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fake = FakePayPal()
        self.demo = Demo(Path(self.temp.name) / "credits.db", PayPalSandbox("mock-id", "mock-secret", opener=self.fake.open))
        self.key = self.demo.create_key()

    def tearDown(self):
        self.demo.close()
        self.temp.cleanup()

    def test_approval_gate_and_single_credit(self):
        self.assertEqual(self.demo.balance(self.key)["balance_usd"], "0.00")
        self.assertEqual(self.demo.demo_answer(self.key, "hello")["status"], "insufficient_credits")
        order = self.demo.request_topup(self.key)
        self.assertTrue(approval_url(order["approval_url"]))
        self.assertNotIn("claim", order)
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "approval_required")
        self.assertEqual(self.demo.balance(self.key)["balance_usd"], "0.00")
        self.fake.approved = True
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "credited")
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "already_credited")
        answer = self.demo.demo_answer(self.key, "hello")
        self.assertEqual((answer["status"], answer["charged_usd"], answer["balance_usd"]),
                         ("answered", "0.001", "0.999"))
        self.assertEqual(len([r for r in self.fake.requests if r.full_url.endswith("/capture")]), 2)

    def test_pending_mismatch_and_already_captured(self):
        order = self.demo.request_topup(self.key)
        self.fake.approved = True
        self.fake.mode = "pending"
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "pending")
        self.fake.mode = "already"
        self.fake.value = "2.00"
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "held_for_review")
        self.assertEqual(self.demo.balance(self.key)["balance_usd"], "0.00")
        self.assertEqual(self.demo.resume_topup(self.key, order["order_id"])["status"], "held_for_review")

    def test_invalid_key_and_foreign_order(self):
        with self.assertRaises(Exception):
            self.demo.request_topup("no-such-key")
        self.assertEqual(self.fake.requests, [])
        order = self.demo.request_topup(self.key)
        other = self.demo.create_key()
        with self.assertRaises(Exception):
            self.demo.resume_topup(other, order["order_id"])
        self.assertEqual(self.demo.balance(other)["balance_usd"], "0.00")

    def test_restart_cannot_capture_or_apply_an_unclaimed_order(self):
        order = self.demo.request_topup(self.key)
        other_process = Demo(self.demo.path, PayPalSandbox("mock-id", "mock-secret", opener=self.fake.open))
        try:
            with self.assertRaises(Exception):
                other_process.resume_topup(self.key, order["order_id"])
            self.assertEqual(other_process.balance(self.key)["balance_usd"], "0.00")
        finally:
            other_process.close()

    def test_local_answer_validation_and_mcp_dispatch(self):
        with self.assertRaises(Exception):
            self.demo.demo_answer(self.key, " ")
        self.assertEqual(self.demo.balance(self.key)["balance_usd"], "0.00")
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "check_credits_balance", "arguments": {"key": self.key}}}
        reply = dispatch(self.demo, msg)
        self.assertEqual(json.loads(reply["result"]["content"][0]["text"])["balance_usd"], "0.00")
        self.assertEqual(len(dispatch(self.demo, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]), 4)
        self.assertIsNone(dispatch(self.demo, {"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_approval_url_rejects_lookalikes(self):
        for url in ("http://www.sandbox.paypal.com/x", "https://www.sandbox.paypal.com.evil.test/x",
                    "https://www.sandbox.paypal.com@evil.test/x", "https://www.paypal.com/x"):
            self.assertFalse(approval_url(url))


if __name__ == "__main__":
    unittest.main()
