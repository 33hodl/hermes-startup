"""Revenue-capable v1 local contracts: map, entitlement, approval, and fake sprint."""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def build_opportunity_map(qualification: dict, profile: dict) -> dict:
    if qualification.get("qualification") != "qualified":
        raise ValueError("a qualified onboarding is required")
    assets = str(profile.get("assets", ""))[:500]
    base = [
        ("sales-diagnostic", "Offer a bounded B2B sales-message diagnostic", "Stated sales experience may support fast service delivery.", ("sales", "outbound", "business development", "account executive", "revenue")),
        ("workflow-rescue", "Offer a fixed-scope Hermes workflow rescue", "Stated technical or automation experience may support a bounded setup service.", ("hermes", "automation", "python", "workflow", "developer", "engineering", "technical")),
        ("research-brief", "Offer a sourced buyer-research brief", "Stated research or writing experience may support a small reversible document deliverable.", ("research", "writing", "analysis", "analyst", "content", "market")),
    ]
    normalized_assets = assets.lower()
    scores = {
        identifier: sum(1 for keyword in keywords if keyword in normalized_assets)
        for identifier, _title, _why, keywords in base
    }
    recommended_id = max(base, key=lambda item: (scores[item[0]], -base.index(item)))[0]
    return {
        "schema_version": "1.0",
        "recommended_id": recommended_id,
        "hypotheses": [
            {"id": i, "title": title, "rationale": why, "evidence_level": "inferred", "uncertainty": "No buyer demand or willingness to pay has been verified.", "profile_basis": assets, "external_action_required": True}
            for i, title, why, _keywords in base
        ],
        "rejected_categories": ["speculation", "spam", "self-purchase"],
    }


def build_first_dollar_map(hypothesis: dict, profile: dict) -> dict:
    required = ("id", "title", "rationale", "evidence_level", "uncertainty")
    if not isinstance(hypothesis, dict) or any(not isinstance(hypothesis.get(key), str) or not hypothesis[key].strip() for key in required):
        raise ValueError("a complete evidence-labeled hypothesis is required")
    if not isinstance(profile, dict):
        raise ValueError("a local onboarding profile is required")

    def bounded(key: str) -> str:
        value = profile.get(key, "Not provided")
        return value[:500] if isinstance(value, str) and value.strip() else "Not provided"

    units = ["buyer", "painful problem", "bounded offer", "ethical channel", "payment proof"]
    sequence = [
        "Verify one reachable buyer group and one problem statement.",
        "Prepare the smallest deliverable that could solve that problem.",
        "Preview one exact demand-test action for approval.",
        "Run only the approved action and record the market response.",
        "Persist, adapt, stop, or switch using the agreed evidence budget.",
    ]
    summary = "\n".join(
        (
            f"Outcome: {bounded('outcome_urgency')}",
            f"Selected path: {hypothesis['title']}",
            f"Why it may fit: {hypothesis['rationale']}",
            f"Starting assets: {bounded('assets')}",
            f"Constraints: {bounded('constraints')}",
            f"Boundaries: {bounded('boundaries')}",
            "Next action: Verify one reachable buyer group and one problem statement.",
            f"Uncertainty: {hypothesis['uncertainty']}",
        )
    )[:2_000]
    return {
        "schema_version": "1.0",
        "status": "prepared_not_market_validated",
        "hypothesis_id": hypothesis["id"],
        "evidence_level": hypothesis["evidence_level"],
        "uncertainty": hypothesis["uncertainty"],
        "framework": {
            "name": "DSSS + CaFE",
            "source": "Tim Ferriss, The 4-Hour Chef one-page framework supplied by the founder",
            "steps": {
                "deconstruction": {"minimum_useful_units": units},
                "selection": {"highest_value_units": ["reachable buyer", "verified problem", "specific payment ask"]},
                "sequencing": {"ordered_actions": sequence},
                "stakes": {"mechanism": "A private checkpoint against the agreed evidence budget; no coercive or public stakes."},
                "compression": {"artifact": "one_page_summary"},
                "frequency": {"feedback_loop": "Review each real buyer response; do not wait for a large batch."},
                "encoding": {"memory_aid": "Buyer -> Problem -> Offer -> Ask -> Proof"},
            },
            "failure_points": ["building before buyer evidence", "changing paths before the evidence budget is used", "counting generated assets as demand"],
            "margin_of_safety": "Use reversible tests, a hard spend cap, exact approval, and a stop rule.",
        },
        "one_page_summary": summary,
        "approval_boundary": "Exact approval is required before every market-facing action or spend.",
    }


def build_managed_sprint_offer(
    qualification: dict,
    commitment: dict,
    *,
    price_cents: int,
    currency: str,
    provider_spend_cap_cents: int,
    deliverables: list[str],
    external_costs: str,
    cancellation_terms: str,
    refund_terms: str,
) -> dict:
    if qualification.get("qualification") != "qualified" or qualification.get("paid_offer_allowed") is not True:
        raise ValueError("a qualified onboarding is required before a managed offer")
    if not isinstance(commitment, dict):
        raise ValueError("a confirmed path is required before a managed offer")
    hypothesis_id = commitment.get("selected_hypothesis")
    evidence_budget = commitment.get("evidence_budget")
    stop_rule = commitment.get("stop_rule")
    if not isinstance(hypothesis_id, str) or not hypothesis_id.strip() or type(evidence_budget) is not int or not 1 <= evidence_budget <= 100 or not isinstance(stop_rule, str) or not stop_rule.strip():
        raise ValueError("a confirmed path, evidence budget, and stop rule are required")
    normalized_currency = currency.upper() if isinstance(currency, str) else ""
    if type(price_cents) is not int or price_cents <= 0 or normalized_currency not in {"USD", "SGD"}:
        raise ValueError("a positive price and supported currency are required")
    if type(provider_spend_cap_cents) is not int or provider_spend_cap_cents < 0:
        raise ValueError("a non-negative provider spend cap is required")
    if not isinstance(deliverables, list) or not 1 <= len(deliverables) <= 10 or any(not isinstance(item, str) or not item.strip() or len(item) > 500 for item in deliverables):
        raise ValueError("one to ten bounded deliverables are required")
    terms = {
        "external_costs": external_costs,
        "cancellation_terms": cancellation_terms,
        "refund_terms": refund_terms,
    }
    if any(not isinstance(value, str) or not value.strip() or len(value) > 2_000 for value in terms.values()):
        raise ValueError("external costs, cancellation terms, and refund terms are required")

    offer = {
        "schema_version": "1.0",
        "status": "test_offer_prepared",
        "payment_type": "one_time",
        "price": {"amount_cents": price_cents, "currency": normalized_currency},
        "selected_hypothesis": hypothesis_id,
        "deliverables": list(deliverables),
        "evidence_budget": evidence_budget,
        "provider_spend_cap_cents": provider_spend_cap_cents,
        "stop_rule": stop_rule,
        **terms,
        "recurring_commitment": False,
        "available_for_live_payment": False,
        "evidence_label": "prepared_not_purchased",
    }
    offer["offer_digest"] = hashlib.sha256(json.dumps(offer, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return offer


class RevenueState:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def _lock(self):
        parent = self.path.parent
        current = Path(self.path.absolute().anchor)
        for part in self.path.absolute().parts[1:-1]:
            current /= part
            if current.is_symlink():
                raise ValueError("state path contains a symlink")
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(self.path) + ".lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.fchmod(fd, 0o600); fcntl.flock(fd, fcntl.LOCK_EX); yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)

    def _empty(self) -> dict:
        return {"schema_version": "1.0", "commitment": None, "offers": {}, "entitlements": [], "processed_events": {}, "jobs": [], "actions": {}, "support": {}}

    def _load(self) -> dict:
        if self.path.is_symlink():
            raise ValueError("state path contains a symlink")
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return self._empty()
        info = self.path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o022:
            raise ValueError("state file is not trusted")
        if len(raw) > 131072:
            raise ValueError("state is oversized")
        value = json.loads(raw)
        expected_keys = {"schema_version", "commitment", "offers", "entitlements", "processed_events", "jobs", "actions", "support"}
        if not isinstance(value, dict) or set(value) != expected_keys or value.get("schema_version") != "1.0":
            raise ValueError("state schema is invalid")
        if value["commitment"] is not None and not isinstance(value["commitment"], dict):
            raise ValueError("state schema is invalid")
        if not isinstance(value["offers"], dict) or not isinstance(value["actions"], dict) or not isinstance(value["support"], dict):
            raise ValueError("state schema is invalid")
        if not isinstance(value["entitlements"], list) or not isinstance(value["processed_events"], dict) or not isinstance(value["jobs"], list):
            raise ValueError("state schema is invalid")
        if value["commitment"] is not None and set(value["commitment"]) != {"selected_hypothesis", "evidence_budget", "stop_rule"}:
            raise ValueError("state schema is invalid")
        for digest, record in value["offers"].items():
            if not isinstance(digest, str) or len(digest) != 64 or not isinstance(record, dict) or set(record) != {"profile_id", "offer"} or not isinstance(record["profile_id"], str) or not isinstance(record["offer"], dict) or record["offer"].get("offer_digest") != digest:
                raise ValueError("state schema is invalid")
            unsigned_offer = {key: item for key, item in record["offer"].items() if key != "offer_digest"}
            expected_digest = hashlib.sha256(json.dumps(unsigned_offer, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if not hmac.compare_digest(digest, expected_digest):
                raise ValueError("state schema is invalid")
        entitlement_keys = {"profile_id", "event_id", "payment_intent_id", "offer_digest", "selected_hypothesis", "status", "mode"}
        for entitlement in value["entitlements"]:
            if not isinstance(entitlement, dict) or set(entitlement) != entitlement_keys or entitlement.get("status") not in {"available", "consumed", "revoked"} or entitlement.get("mode") != "test":
                raise ValueError("state schema is invalid")
        for event_id, fingerprint in value["processed_events"].items():
            if not isinstance(event_id, str) or not event_id or not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(character not in "0123456789abcdef" for character in fingerprint):
                raise ValueError("state schema is invalid")
        for digest, action in value["actions"].items():
            if not isinstance(digest, str) or not isinstance(action, dict) or set(action) not in ({"kind", "target", "content", "digest", "status"}, {"kind", "target", "content", "digest", "status", "execution"}) or action.get("digest") != digest or action.get("status") not in {"prepared", "approved", "executed"}:
                raise ValueError("state schema is invalid")
        return value

    def _save(self, value: dict) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, prefix=".revenue.", delete=False) as handle:
                temporary = Path(handle.name); os.fchmod(handle.fileno(), 0o600)
                json.dump(value, handle, sort_keys=True, separators=(",", ":")); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.path); temporary = None
        finally:
            if temporary: temporary.unlink(missing_ok=True)

    def snapshot(self) -> dict:
        with self._lock(): return json.loads(json.dumps(self._load()))

    def delete(self) -> bool:
        with self._lock():
            if not self._deletable_unlocked():
                return False
            self.path.unlink()
            return True

    def validate_deletable(self) -> bool:
        with self._lock():
            return self._deletable_unlocked()

    def _deletable_unlocked(self) -> bool:
        if self.path.is_symlink():
            raise ValueError("state path contains a symlink")
        try:
            info = self.path.stat()
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("state file is not trusted")
        return True

    def confirm_path(self, hypothesis_id: str, *, evidence_budget: int, stop_rule: str) -> dict:
        if not hypothesis_id or type(evidence_budget) is not int or not 1 <= evidence_budget <= 100 or not stop_rule:
            raise ValueError("path, bounded evidence budget, and stop rule are required")
        with self._lock():
            state = self._load(); commitment = {"selected_hypothesis": hypothesis_id, "evidence_budget": evidence_budget, "stop_rule": stop_rule}
            state["commitment"] = commitment; self._save(state); return commitment

    def save_prepared_offer(self, profile_id: str, offer: dict) -> dict:
        if not isinstance(profile_id, str) or not profile_id.strip() or len(profile_id) > 128 or any(ord(character) < 33 or ord(character) > 126 for character in profile_id) or not isinstance(offer, dict):
            raise ValueError("profile and prepared offer are required")
        digest = offer.get("offer_digest")
        unsigned = {key: value for key, value in offer.items() if key != "offer_digest"}
        expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if offer.get("status") != "test_offer_prepared" or offer.get("available_for_live_payment") is not False or not isinstance(digest, str) or not hmac.compare_digest(digest, expected):
            raise ValueError("prepared offer digest is invalid")
        record = {"profile_id": profile_id, "offer": json.loads(json.dumps(offer))}
        with self._lock():
            state = self._load()
            commitment = state.get("commitment")
            if not isinstance(commitment, dict) or any(
                commitment.get(key) != offer.get(offer_key)
                for key, offer_key in (("selected_hypothesis", "selected_hypothesis"), ("evidence_budget", "evidence_budget"), ("stop_rule", "stop_rule"))
            ):
                raise ValueError("prepared offer does not match the committed path")
            existing = state.setdefault("offers", {}).get(digest)
            if existing is not None:
                if not isinstance(existing, dict) or existing.get("profile_id") != profile_id or existing.get("offer") != record["offer"]:
                    raise ValueError("prepared offer is already bound to another profile")
                return json.loads(json.dumps(existing))
            state.setdefault("offers", {})[digest] = record
            self._save(state)
        return json.loads(json.dumps(record))

    def grant_test_entitlement(self, profile_id: str, event_id: str, offer_digest: str, *, payment_intent_id: str, event_fingerprint: str | None = None) -> dict:
        if not profile_id or not event_id or not payment_intent_id or not isinstance(offer_digest, str) or len(offer_digest) != 64 or any(character not in "0123456789abcdef" for character in offer_digest):
            raise ValueError("profile, event, payment intent, and prepared offer digest are required")
        with self._lock():
            state = self._load()
            fingerprint = event_fingerprint or _digest(profile_id, event_id, offer_digest, payment_intent_id)
            recorded_fingerprint = state["processed_events"].get(event_id)
            if recorded_fingerprint is not None and recorded_fingerprint != fingerprint:
                raise ValueError("event is already bound to different transaction data")
            prepared = state["offers"].get(offer_digest)
            if not isinstance(prepared, dict):
                raise ValueError("prepared offer is required before granting an entitlement")
            if prepared.get("profile_id") != profile_id:
                raise ValueError("prepared offer is bound to another profile")
            selected_hypothesis = prepared.get("offer", {}).get("selected_hypothesis")
            if not isinstance(selected_hypothesis, str) or not selected_hypothesis:
                raise ValueError("prepared offer is not bound to a hypothesis")
            existing = next((e for e in state["entitlements"] if e["event_id"] == event_id), None)
            if existing:
                if any(existing.get(key) != value for key, value in (("profile_id", profile_id), ("offer_digest", offer_digest), ("payment_intent_id", payment_intent_id), ("selected_hypothesis", selected_hypothesis))):
                    raise ValueError("event is already bound to another transaction")
                return existing
            if any(entitlement.get("payment_intent_id") == payment_intent_id for entitlement in state["entitlements"]):
                raise ValueError("payment intent is already bound to an entitlement")
            item = {"profile_id": profile_id, "event_id": event_id, "payment_intent_id": payment_intent_id, "offer_digest": offer_digest, "selected_hypothesis": selected_hypothesis, "status": "available", "mode": "test"}
            state["entitlements"].append(item); state["processed_events"][event_id] = fingerprint; self._save(state); return item

    def prepare_action(self, kind: str, target: str, content: str) -> dict:
        if not kind or not target or not content: raise ValueError("action preview fields are required")
        digest = _digest(kind, target, content)
        with self._lock():
            state = self._load(); item = {"kind": kind, "target": target, "content": content, "digest": digest, "status": "prepared"}
            state["actions"][digest] = item; self._save(state); return item

    def approve_action(self, digest: str) -> dict:
        with self._lock():
            state = self._load(); item = state["actions"].get(digest)
            if not item: raise ValueError("unknown action")
            item["status"] = "approved"; self._save(state); return item

    def execute_sandboxed_action(self, digest: str, *, content: str) -> dict:
        with self._lock():
            state = self._load(); item = state["actions"].get(digest)
            if not item: raise ValueError("unknown action")
            if _digest(item["kind"], item["target"], content) != digest: raise ValueError("action content changed; approval invalid")
            if item["status"] == "executed": raise RuntimeError("action already executed")
            if item["status"] != "approved": raise RuntimeError("exact approval required")
            item["status"] = "executed"; item["execution"] = "sandboxed_only"; self._save(state)
            return {"status": "sandboxed_only", "digest": digest, "external_write": False}

    def preview_support_ticket(self, category: str, message: str) -> dict:
        if category not in {"help", "bug", "feedback", "billing", "privacy"} or not message: raise ValueError("valid support category and message required")
        digest = _digest(category, message)
        with self._lock():
            state = self._load(); state["support"][digest] = {"category": category, "message": message, "status": "previewed"}; self._save(state)
        return {"digest": digest, "category": category, "message": message, "outbound_metadata": {}}

    def approve_support_ticket(self, digest: str) -> None:
        with self._lock():
            state = self._load(); ticket = state["support"].get(digest)
            if not ticket: raise ValueError("unknown support preview")
            ticket["status"] = "approved"; self._save(state)

    def queue_support_ticket(self, digest: str, message: str) -> dict:
        with self._lock():
            state = self._load(); ticket = state["support"].get(digest)
            if not ticket or ticket["status"] != "approved": raise RuntimeError("exact support approval required")
            if _digest(ticket["category"], message) != digest: raise ValueError("support message changed; approval invalid")
            ticket["status"] = "queued_local"; self._save(state)
            return {"ticket_id": digest[:16], "status": "queued_local", "telegram_sent": False}


def checkout_payload(state: RevenueState, profile_id: str, *, stripe_mode: str, success_url: str | None = None, cancel_url: str | None = None, offer_digest: str | None = None) -> dict:
    if not success_url or not cancel_url or not success_url.startswith("https://") or not cancel_url.startswith("https://"):
        raise ValueError("HTTPS success and cancel URLs are required")
    if stripe_mode != "test":
        raise ValueError("only explicit Stripe test mode checkout is allowed")
    if not profile_id:
        raise ValueError("valid profile is required")
    if not isinstance(offer_digest, str) or len(offer_digest) != 64 or any(character not in "0123456789abcdef" for character in offer_digest):
        raise ValueError("a valid prepared offer digest is required")
    prepared = state.snapshot().get("offers", {}).get(offer_digest)
    if not isinstance(prepared, dict) or prepared.get("profile_id") != profile_id:
        raise ValueError("checkout is not bound to a prepared offer for this profile")
    offer = prepared.get("offer", {})
    if offer.get("status") != "test_offer_prepared" or offer.get("evidence_label") != "prepared_not_purchased" or offer.get("payment_type") != "one_time" or offer.get("available_for_live_payment") is not False:
        raise ValueError("prepared offer is not eligible for test checkout")
    price = offer.get("price", {})
    price_cents = price.get("amount_cents")
    currency = price.get("currency")
    if type(price_cents) is not int or price_cents <= 0 or not isinstance(currency, str) or currency.lower() not in {"usd", "sgd"}:
        raise ValueError("prepared offer price is invalid")
    return {"mode": "payment", "execution_mode": "stripe_test_only", "success_url": success_url, "cancel_url": cancel_url, "line_items[0][price_data][currency]": currency.lower(), "line_items[0][price_data][unit_amount]": price_cents, "line_items[0][price_data][product_data][name]": "One-time managed validation sprint", "line_items[0][quantity]": 1, "metadata[profile_id]": profile_id, "metadata[offer_digest]": offer_digest, "metadata[execution_mode]": "stripe_test_only", "payment_intent_data[metadata][profile_id]": profile_id, "payment_intent_data[metadata][offer_digest]": offer_digest, "payment_intent_data[metadata][execution_mode]": "stripe_test_only"}


def _verify_signature(body: bytes, header: str, secret: str, *, now: int, tolerance: int = 300) -> None:
    fields = {}
    for part in header.split(","):
        if "=" in part:
            key, value = part.split("=", 1); fields.setdefault(key, []).append(value)
    try: timestamp = int(fields["t"][0])
    except (KeyError, ValueError): raise ValueError("invalid webhook signature") from None
    if abs(now - timestamp) > tolerance: raise ValueError("invalid webhook signature timestamp")
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, value) for value in fields.get("v1", [])):
        raise ValueError("invalid webhook signature")


def handle_stripe_webhook(body: bytes, signature_header: str, secret: str, state: RevenueState, *, now: int | None = None) -> dict:
    if not secret: raise ValueError("webhook secret required")
    _verify_signature(body, signature_header, secret, now=int(time.time()) if now is None else now)
    event = json.loads(body)
    event_id = event.get("id") if isinstance(event, dict) else None
    if not event_id: raise ValueError("event id required")
    if event.get("livemode") is not False: raise ValueError("only Stripe test mode events are accepted")
    event_fingerprint = hashlib.sha256(body).hexdigest()
    recorded_fingerprint = state.snapshot()["processed_events"].get(event_id)
    if recorded_fingerprint is not None:
        if not hmac.compare_digest(recorded_fingerprint, event_fingerprint):
            raise ValueError("event id was reused with different transaction data")
        return {"status": "duplicate", "event_id": event_id}
    obj = event.get("data", {}).get("object", {})
    profile_id = obj.get("metadata", {}).get("profile_id")
    offer_digest = obj.get("metadata", {}).get("offer_digest")
    if event.get("type") == "charge.refunded":
        payment_intent_id = obj.get("payment_intent")
        if not profile_id or not offer_digest or not payment_intent_id:
            raise ValueError("refund is not bound to a profile, offer, and payment intent")
        with state._lock():
            data = state._load()
            entitlement = next((item for item in data["entitlements"] if item.get("profile_id") == profile_id and item.get("offer_digest") == offer_digest and item.get("payment_intent_id") == payment_intent_id), None)
            if entitlement is None:
                raise ValueError("refund does not match a known entitlement")
            if entitlement["status"] == "available":
                entitlement["status"] = "revoked"
            data["processed_events"][event_id] = event_fingerprint; state._save(data)
        return {"status": "revoked" if entitlement["status"] == "revoked" else "refund_recorded", "event_id": event_id, "profile_id": profile_id}
    if event.get("type") != "checkout.session.completed" or obj.get("payment_status") != "paid" or not profile_id:
        return {"status": "ignored", "event_id": event_id}
    if not isinstance(offer_digest, str) or len(offer_digest) != 64 or any(character not in "0123456789abcdef" for character in offer_digest):
        raise ValueError("a valid prepared offer digest is required")
    prepared = state.snapshot().get("offers", {}).get(offer_digest)
    if not isinstance(prepared, dict) or prepared.get("profile_id") != profile_id:
        raise ValueError("payment is not bound to a prepared offer for this profile")
    prepared_price = prepared.get("offer", {}).get("price", {})
    if obj.get("mode") != "payment":
        raise ValueError("only one-time payment mode is accepted")
    if type(obj.get("amount_total")) is not int or obj.get("amount_total") != prepared_price.get("amount_cents") or obj.get("currency") != str(prepared_price.get("currency", "")).lower():
        raise ValueError("payment price does not match the prepared offer")
    payment_intent_id = obj.get("payment_intent")
    if not isinstance(payment_intent_id, str) or not payment_intent_id:
        raise ValueError("payment intent is required")
    state.grant_test_entitlement(profile_id, event_id, offer_digest, payment_intent_id=payment_intent_id, event_fingerprint=event_fingerprint)
    return {"status": "granted", "event_id": event_id, "profile_id": profile_id}


def run_fake_managed_sprint(state: RevenueState, profile_id: str, hypothesis_id: str) -> dict:
    with state._lock():
        data = state._load()
        commitment = data.get("commitment")
        if not isinstance(commitment, dict) or commitment.get("selected_hypothesis") != hypothesis_id:
            raise RuntimeError("managed work must match the committed hypothesis")
        entitlement = next((e for e in data["entitlements"] if e["profile_id"] == profile_id and e["selected_hypothesis"] == hypothesis_id and e["status"] == "available"), None)
        if not entitlement or entitlement["status"] != "available": raise RuntimeError("entitlement missing or already consumed")
        entitlement["status"] = "consumed"
        result = {"job_id": _digest(profile_id, hypothesis_id)[:16], "hypothesis_id": hypothesis_id, "provider": "deterministic_fake", "estimated_cost_cents": 0, "actual_cost_cents": 0, "sources": [{"url": "mock://managed-validation", "trust": "mock"}], "decision_change": "No real-world claim; ready for a separately approved market test."}
        data["jobs"].append(result); state._save(data); return result


def route_revenue_intent(text: str) -> str:
    normalized = " ".join(text.lower().strip().split())
    if "support replies" in normalized or "ticket status" in normalized:
        return "support_status"
    if "budget" in normalized or "spend cap" in normalized:
        return "budget"
    if normalized.startswith("/support") or any(term in normalized for term in ("bug", "payment failed", "need help", "contact support", "feedback")):
        return "support"
    if normalized in {"/startup", "/radar", "start", "onboarding"} or any(term in normalized for term in ("first dollar", "make money", "earn online")):
        return "onboarding"
    return "status"
