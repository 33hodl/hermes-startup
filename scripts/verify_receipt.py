#!/usr/bin/env python3
"""Verify a signed agent-commerce receipt offline.

The `scripts/sell_to_agents.py` storefront signs every completed order with a
detached Ed25519 signature over a canonical JSON payload. This script is the
buyer-side counterpart: it checks that signature against the merchant's public
JWK and, optionally, that a delivered file matches the signed digest.

    verify_receipt.py receipt.json --jwk https://store.example/receipts/key
    verify_receipt.py receipt.json --jwk jwk.json --deliverable report.pdf
    pbpaste | verify_receipt.py - --jwk jwk.json

Exit codes: 0 valid, 1 invalid, 2 unusable input. Nothing here calls back into
the merchant: a receipt is checked with the payload, the signature and the key.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

RECEIPT_VERSION = "1"
_SIGNATURE = re.compile(r"^[A-Za-z0-9_-]+$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_FIELDS = (
    "receipt_version",
    "merchant",
    "order_id",
    "order_number",
    "checkout_session_id",
    "items",
    "amount",
    "currency",
    "payment_status",
    "deliverable_sha256",
    "created_at",
)


class InvalidReceipt(Exception):
    """The receipt or key cannot be accepted."""


def canonical_json(value: Any) -> str:
    """Sorted keys, no incidental whitespace: the exact bytes that were signed."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not _SIGNATURE.match(value):
        raise InvalidReceipt("signature is not unpadded base64url")
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def load_jwk(source: str) -> dict[str, Any]:
    """Read a JWK from inline JSON, a file path or an http(s) URL."""
    text = source.strip()
    if text.startswith("{"):
        payload = text
    elif text.startswith(("http://", "https://")):
        request = urllib.request.Request(text, headers={"accept": "application/json"})
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - caller-supplied URL by design
            payload = response.read().decode("utf-8")
    else:
        payload = Path(text).read_text(encoding="utf-8")
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise InvalidReceipt(f"JWK is not JSON: {exc}") from exc
    # Accept either the bare JWK or {"keys": [...]} / {"jwk": {...}} wrappers.
    if isinstance(document, dict) and isinstance(document.get("keys"), list):
        document = document["keys"][0] if document["keys"] else {}
    if isinstance(document, dict) and isinstance(document.get("jwk"), dict):
        document = document["jwk"]
    if not isinstance(document, dict):
        raise InvalidReceipt("JWK must be a JSON object")
    if document.get("kty") != "OKP" or document.get("crv") != "Ed25519":
        raise InvalidReceipt("JWK must be an Ed25519 (OKP/crv=Ed25519) key")
    if not isinstance(document.get("x"), str):
        raise InvalidReceipt("JWK is missing its public x coordinate")
    return document


def _public_key(jwk: dict[str, Any]):
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:  # pragma: no cover - environment guard
        raise InvalidReceipt("the cryptography package is required to verify receipts") from exc
    raw = _b64url_decode(jwk["x"])
    if len(raw) != 32:
        raise InvalidReceipt("JWK public key must be 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def check_shape(receipt: dict[str, Any]) -> dict[str, Any]:
    """Reject structurally wrong receipts before any crypto is attempted."""
    if not isinstance(receipt, dict):
        raise InvalidReceipt("receipt must be a JSON object")
    if receipt.get("alg") != "Ed25519":
        raise InvalidReceipt("receipt.alg must be Ed25519")
    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        raise InvalidReceipt("receipt.payload must be a JSON object")
    missing = [field for field in _FIELDS if field not in payload]
    if missing:
        raise InvalidReceipt("payload is missing " + ", ".join(missing))
    if payload["receipt_version"] != RECEIPT_VERSION:
        raise InvalidReceipt(f"unsupported receipt_version {payload['receipt_version']!r}")
    if type(payload["amount"]) is not int or payload["amount"] < 0:
        raise InvalidReceipt("payload.amount must be a non-negative integer in minor units")
    for field in ("merchant", "order_id", "order_number", "checkout_session_id", "currency", "payment_status"):
        if not isinstance(payload[field], str) or not payload[field]:
            raise InvalidReceipt(f"payload.{field} must be a non-empty string")
    items = payload["items"]
    if not isinstance(items, list) or not items:
        raise InvalidReceipt("payload.items must be a non-empty list")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise InvalidReceipt(f"payload.items[{index}] must be an object")
        if not isinstance(item.get("product_id"), str) or not item["product_id"]:
            raise InvalidReceipt(f"payload.items[{index}].product_id must be a non-empty string")
        if type(item.get("quantity")) is not int or item["quantity"] < 1:
            raise InvalidReceipt(f"payload.items[{index}].quantity must be a positive integer")
        if type(item.get("unit_amount")) is not int or item["unit_amount"] < 0:
            raise InvalidReceipt(f"payload.items[{index}].unit_amount must be a non-negative integer")
    deliverable = payload["deliverable_sha256"]
    if deliverable is not None and (not isinstance(deliverable, str) or not _SHA256.match(deliverable.lower())):
        raise InvalidReceipt("payload.deliverable_sha256 must be null or 64 hex characters")
    return payload


def verify(receipt: dict[str, Any], jwk: dict[str, Any]) -> dict[str, Any]:
    """Return the verified payload, or raise InvalidReceipt."""
    payload = check_shape(receipt)
    key_id = receipt.get("key_id")
    if isinstance(key_id, str) and jwk.get("kid") and key_id != jwk["kid"]:
        raise InvalidReceipt(f"receipt key_id {key_id!r} does not match JWK kid {jwk['kid']!r}")
    signature = _b64url_decode(receipt.get("signature", ""))
    if len(signature) != 64:
        raise InvalidReceipt("signature must be 64 bytes")
    try:
        _public_key(jwk).verify(signature, canonical_json(payload).encode("utf-8"))
    except InvalidReceipt:
        raise
    except Exception as exc:  # noqa: BLE001 - any failure here is an invalid signature
        raise InvalidReceipt("signature does not verify against this key") from exc
    return payload


def check_deliverable(payload: dict[str, Any], path: str) -> str:
    expected = payload.get("deliverable_sha256")
    if not expected:
        raise InvalidReceipt("receipt carries no deliverable_sha256 to compare")
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != expected.lower():
        raise InvalidReceipt(f"deliverable hash mismatch: receipt {expected.lower()}, file {digest}")
    return digest


def _read_receipt(source: str) -> dict[str, Any]:
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    document = json.loads(text)
    # Tolerate the whole order/checkout envelope: {"order": {"receipt": {...}}}.
    for _ in range(2):
        if not isinstance(document, dict):
            break
        if isinstance(document.get("receipt"), dict):
            document = document["receipt"]
        elif isinstance(document.get("order"), dict):
            document = document["order"]
        else:
            break
    return document


def _resolve_key_source(args: argparse.Namespace, receipt: dict[str, Any]) -> str:
    """Return the explicit JWK source, or refuse the attacker-controlled key_url.

    A receipt is untrusted input, so its embedded key_url must never be fetched
    by default (SSRF + key-substitution). Only an explicit --jwk/--jwk-file or a
    positively opted-in --allow-key-url https URL is accepted, and an opted-in
    URL must satisfy the --key-host allowlist when one is supplied.
    """
    if args.jwk_file:
        return args.jwk_file
    if args.jwk:
        return args.jwk
    if args.allow_key_url:
        key_url = receipt.get("key_url")
        if not isinstance(key_url, str) or not key_url:
            raise InvalidReceipt("--allow-key-url set but the receipt has no usable key_url")
        parsed = urllib.parse.urlparse(key_url)
        if parsed.scheme != "https":
            raise InvalidReceipt("key_url must use https when --allow-key-url is used")
        host = parsed.hostname
        if not host:
            raise InvalidReceipt(f"key_url {key_url!r} has no host")
        if args.key_host and host not in args.key_host:
            raise InvalidReceipt(f"key_url host {host!r} is not in the --key-host allowlist")
        return key_url
    raise InvalidReceipt("no --jwk given; the receipt key_url is ignored by default (pass --allow-key-url to opt in)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a signed agent-commerce receipt offline.")
    parser.add_argument("receipt", help="receipt JSON file, or - for stdin")
    parser.add_argument("--jwk", help="merchant JWK: inline JSON, file path or https URL")
    parser.add_argument("--jwk-file", help="path to a merchant JWK JSON file")
    parser.add_argument(
        "--allow-key-url",
        action="store_true",
        help="read the verification key from receipt.key_url (only https; --key-host allowlist optional)",
    )
    parser.add_argument(
        "--key-host",
        action="append",
        default=[],
        help="host allowed for --allow-key-url (repeatable)",
    )
    parser.add_argument("--deliverable", help="file whose SHA-256 must match payload.deliverable_sha256")
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args(argv)

    try:
        receipt = _read_receipt(args.receipt)
        payload = check_shape(receipt)  # validate the receipt before any key fetch
        source = _resolve_key_source(args, receipt)
        jwk = load_jwk(source)
        payload = verify(receipt, jwk)
        deliverable = check_deliverable(payload, args.deliverable) if args.deliverable else None
    except InvalidReceipt as exc:
        if args.json:
            print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        else:
            print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        if args.json:
            print(json.dumps({"valid": False, "error": f"unreadable input: {exc}"}, sort_keys=True))
        else:
            print(f"UNUSABLE: {exc}", file=sys.stderr)
        return 2

    result = {
        "valid": True,
        "order_id": payload["order_id"],
        "merchant": payload["merchant"],
        "amount": payload["amount"],
        "currency": payload["currency"],
        "payment_status": payload["payment_status"],
        "deliverable_sha256": payload["deliverable_sha256"],
        "deliverable_matches": deliverable is not None,
        "key_id": receipt.get("key_id"),
        "signature": _b64url_encode(_b64url_decode(receipt["signature"]))[:16] + "…",
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        amount = f"{payload['amount'] / 100:.2f} {payload['currency']}"
        print(f"VALID receipt for {payload['order_id']} — {amount} at {payload['merchant']}")
        print(f"  payment_status: {payload['payment_status']}")
        if deliverable:
            print(f"  deliverable matches signed sha256 {deliverable}")
        elif payload.get("deliverable_sha256"):
            print(f"  signed deliverable sha256: {payload['deliverable_sha256']} (not checked; pass --deliverable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
