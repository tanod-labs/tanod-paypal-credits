"""Small PayPal Orders v2 sandbox adapter. No live-mode switch exists."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

API = "https://api-m.sandbox.paypal.com"


class PayPalError(Exception):
    """A sanitized API error; response bodies and credentials are never included."""


@dataclass(frozen=True)
class Order:
    order_id: str
    approve_url: str


@dataclass(frozen=True)
class Capture:
    status: str
    capture_id: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    custom_id: str | None = None


def approval_url(url: str) -> bool:
    p = urlsplit(url)
    return p.scheme == "https" and p.hostname == "www.sandbox.paypal.com" and not p.username and not p.password


def parse_capture(body: dict) -> Capture:
    units = body.get("purchase_units")
    unit = units[0] if isinstance(units, list) and units and isinstance(units[0], dict) else {}
    payments = unit.get("payments") if isinstance(unit.get("payments"), dict) else {}
    captures = payments.get("captures") if isinstance(payments.get("captures"), list) else []
    caps = [c for c in captures if isinstance(c, dict)]
    if not caps:
        status = body.get("status", "")
        if status in ("CREATED", "SAVED", "PAYER_ACTION_REQUIRED", "APPROVED"):
            return Capture("not_approved")
        if status == "VOIDED":
            return Capture("declined")
        raise PayPalError("PayPal returned an order without a capture")
    cap = next((c for c in caps if c.get("status") == "COMPLETED"), caps[0])
    status = {"COMPLETED": "completed", "PENDING": "pending"}.get(cap.get("status"), "declined")
    amount = cap.get("amount") if isinstance(cap.get("amount"), dict) else {}
    try:
        value = Decimal(str(amount["value"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        value = None
    return Capture(status, str(cap["id"]) if cap.get("id") else None, value,
                   amount.get("currency_code"), cap.get("custom_id") or unit.get("custom_id"))


class PayPalSandbox:
    def __init__(self, client_id: str, client_secret: str, *, opener=None):
        if not client_id or not client_secret:
            raise ValueError("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET for sandbox")
        self._id = client_id
        self._secret = client_secret
        self._open = opener or urllib.request.urlopen
        self._token: str | None = None

    @classmethod
    def from_env(cls, *, opener=None) -> PayPalSandbox:
        # Explicit guard, even though API is a sandbox constant. Never expose secrets in exceptions.
        if os.getenv("PAYPAL_ENV", "sandbox") != "sandbox":
            raise ValueError("This demo accepts PAYPAL_ENV=sandbox only")
        return cls(os.getenv("PAYPAL_CLIENT_ID", ""), os.getenv("PAYPAL_CLIENT_SECRET", ""), opener=opener)

    def _request(self, method: str, path: str, *, body: dict | None = None,
                 token: bool = True, request_id: str | None = None) -> tuple[int, dict]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {self._access_token()}"
            headers["Prefer"] = "return=representation"
        else:
            basic = base64.b64encode(f"{self._id}:{self._secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        if path == "/v1/oauth2/token":
            data = b"grant_type=client_credentials"
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
            if data is not None:
                headers["Content-Type"] = "application/json"
        req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
        try:
            with self._open(req, timeout=15) as response:
                status, raw = response.status, response.read(1_000_001)
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read(1_000_001)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise PayPalError("PayPal sandbox is unavailable; retry later") from None
        if len(raw) > 1_000_000:
            raise PayPalError("PayPal sandbox returned an oversized response")
        try:
            answer = json.loads(raw) if raw else {}
        except (ValueError, UnicodeDecodeError):
            raise PayPalError(f"PayPal sandbox returned invalid JSON (HTTP {status})") from None
        if not isinstance(answer, dict):
            raise PayPalError(f"PayPal sandbox returned invalid JSON (HTTP {status})")
        return status, answer

    def _access_token(self) -> str:
        if self._token:
            return self._token
        status, body = self._request("POST", "/v1/oauth2/token", token=False)
        if status != 200 or not isinstance(body.get("access_token"), str) or not body["access_token"]:
            raise PayPalError(f"Sandbox OAuth failed (HTTP {status})")
        self._token = body["access_token"]
        return self._token

    def create_order(self, *, pack: str, price_usd: str, return_url: str, cancel_url: str) -> Order:
        for url in (return_url, cancel_url):
            if urlsplit(url).scheme != "https":
                raise ValueError("PayPal return/cancel URLs must use HTTPS")
        body = {"intent": "CAPTURE", "purchase_units": [{"reference_id": "tanod-demo-credits",
                "custom_id": f"tanod-demo-credits-{pack}", "description": "Sandbox demo prepaid tool credits",
                "amount": {"currency_code": "USD", "value": price_usd}}],
                "payment_source": {"paypal": {"experience_context": {
                    "brand_name": "Tanod demo", "shipping_preference": "NO_SHIPPING", "user_action": "PAY_NOW",
                    "return_url": return_url, "cancel_url": cancel_url}}}}
        status, answer = self._request("POST", "/v2/checkout/orders", body=body, request_id=str(uuid.uuid4()))
        if status not in (200, 201):
            raise PayPalError(f"Sandbox order creation failed (HTTP {status})")
        oid = answer.get("id")
        links = answer.get("links", [])
        urls = [link.get("href") for link in links if isinstance(link, dict) and
                link.get("rel") in ("payer-action", "approve")] if isinstance(links, list) else []
        url = next((u for u in urls if isinstance(u, str) and approval_url(u)), None)
        if not isinstance(oid, str) or not oid or len(oid) > 64 or not oid.isalnum() or not url:
            raise PayPalError("Sandbox order reply lacks a valid order ID or approval URL")
        return Order(oid, url)

    def get_order(self, order_id: str) -> Capture:
        status, answer = self._request("GET", f"/v2/checkout/orders/{order_id}")
        if status == 404:
            return Capture("unknown_order")
        if status != 200:
            raise PayPalError(f"Sandbox order lookup failed (HTTP {status})")
        return parse_capture(answer)

    def capture(self, order_id: str) -> Capture:
        status, answer = self._request("POST", f"/v2/checkout/orders/{order_id}/capture", body={},
                                       request_id=f"tanod-demo-capture-{order_id}")
        if status in (200, 201):
            return parse_capture(answer)
        if status == 404:
            return Capture("unknown_order")
        if status == 422:
            details = answer.get("details", [])
            issue = details[0].get("issue") if isinstance(details, list) and details and isinstance(details[0], dict) else None
            if issue in ("ORDER_ALREADY_CAPTURED", "DUPLICATE_INVOICE_ID"):
                return self.get_order(order_id)
            if issue in ("ORDER_NOT_APPROVED", "PAYER_ACTION_REQUIRED"):
                return Capture("not_approved")
            return Capture("declined")
        raise PayPalError(f"Sandbox capture failed (HTTP {status}); retry with the same order ID")
