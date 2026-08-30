"""Deterministic local conversation adapter for the Hermes Startup skill."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .flexcard import render_flex_card
from .onboarding import answer_onboarding, delete_onboarding, load_onboarding, qualify_onboarding, start_onboarding, validate_onboarding_deletable
from .revenue_v1 import RevenueState, build_startup_guidance, build_managed_sprint_offer, build_opportunity_map
from .wallet import WalletUnavailable, api_base_url, fetch_wallet_balance


TEST_OFFER_TERMS = {
    "price_cents": 1_000,
    "currency": "USD",
    "provider_spend_cap_cents": 0,
    "deliverables": ["One sourced validation brief", "One exact market-action preview"],
    "external_costs": "None included or required for this local test preview.",
    "cancellation_terms": "Cancel before managed work starts for a full test-mode refund.",
    "refund_terms": "Refund unused managed work if Hermes Startup cannot deliver the stated test scope.",
}

# Safe, generic, true-for-everyone custom lines for the questions_complete share
# card. They never contain answer text, an idea title, or any personal/proprietary
# fact (see UGC_PLAYBOOK.md safe/unsafe rules).
_QUESTION_COMPLETE_OPTIONS = (
    "Three ideas, custom to me",
    "Answered all 10 questions in one sitting",
    "A fresh direction from my own answers",
)
_SHARE_POPUP_COPY = {
    "header": "Your 3 ideas are ready.",
    "prompt": "Want a card to share them? (Your choice, nothing personal.)",
    "decline": "No thanks",
}
_SHARE_STATE_FILE = "share.json"
_SHARE_CARD_FILE = "share-questions-complete.svg"
_QUESTIONS_COMPLETE_MILESTONE = "questions_complete"

def _load_share_state(state_dir: Path) -> dict[str, Any]:
    path = state_dir / _SHARE_STATE_FILE
    try:
        if not path.exists() or path.is_symlink():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_share_state(state_dir: Path, data: dict[str, Any]) -> None:
    path = state_dir / _SHARE_STATE_FILE
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _incomplete_response(state: dict[str, Any], *, phase: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "phase": phase,
        "status": "incomplete",
        "next_question": state["next_question"],
        "paid_offer_allowed": False,
        "next_action": "Answer this one question, or explicitly use prefer_not_to_say.",
        "privacy": {"local_only": True, "external_writes": 0},
    }


def _completed_response(onboarding_path: Path) -> dict[str, Any]:
    qualification = qualify_onboarding(onboarding_path)
    if qualification["qualification"] != "qualified":
        gap = qualification["gaps"][0]
        return {
            "schema_version": "1.0",
            "phase": "complete",
            "status": "not_yet",
            "paid_offer_allowed": False,
            "next_action": gap,
            "evidence_label": "confirmed",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    loaded = load_onboarding(onboarding_path)
    assert loaded is not None
    opportunity_map = build_opportunity_map(qualification, loaded["answers"])
    hypotheses = opportunity_map["hypotheses"]
    shown = opportunity_map["shown"]
    recommended_id = opportunity_map["recommended_id"]
    # Free tier contract: exactly `shown` ideas (3 of 10), recommended one
    # first, then the rest in pool order. The full pool (all hypotheses) is
    # what the paid continuation grades and ranks.
    ordered = [next(h for h in hypotheses if h["id"] == recommended_id)] + [
        h for h in hypotheses if h["id"] != recommended_id
    ]
    ideas = [
        {
            "id": item["id"],
            "title": item["title"],
            "what_it_is": item["what_it_is"],
            "why_chosen": item["why_chosen"],
            "execution_plan": item["execution_plan"],
            "potential": item["potential"],
            "timeframe": item["timeframe"],
            "rationale": item["rationale"],
            "evidence_level": item["evidence_level"],
            "uncertainty": item["uncertainty"],
        }
        for item in ordered[:shown]
    ]
    return {
        "schema_version": "1.0",
        "phase": "complete",
        "status": "qualified",
        "evidence_label": "inferred",
        "ideas": ideas,
        "idea_sampling": {
            "shown": opportunity_map["shown"],
            "pool_total": opportunity_map["pool_total"],
            "is_top_three": False,
            "note": (
                "These are 3 of 10 potential ideas for you - a generous sample "
                "worth building on, not a ranking and not 'the top three'. "
                "The full set of 10, each graded and ranked with the reasons "
                "why, is what the paid continuation unlocks."
            ),
        },
        "paid_offer_allowed": False,
        "continuation_preview": {
            "status": "live",
            "price": "US$10",
            "headline": "A money-making business, built for you.",
            "payment": "US$10 top-up funds the API calls used to start building the chosen business.",
            "billing": "Prepaid balance. No subscriptions. Pay as you go, and auto top-up keeps you running.",
            "benefit": "Hermes Startup gives your Hermes Agent the capabilities it needs to make your first $1.",
            "included": [
                "The full set: all 10 ideas, each graded and ranked with the reason why",
                "Compare and choose among 10 business ideas ranked for fit, not just listed",
                "One shared balance for pay-per-call access to 1,000+ API tools from 20+ providers",
                "Hermes Startup automatically selects the right tools for the work",
            ],
            "boundary": "Checkout is live. Payment is processed by Stripe; prepaid balance, no subscription, auto top-up only when you turn it on. External actions and provider calls still require your explicit approval.",
        },
        "share_offer": {
            "milestone": _QUESTIONS_COMPLETE_MILESTONE,
            "options": list(_QUESTION_COMPLETE_OPTIONS),
            "declined": False,
            "copy": _SHARE_POPUP_COPY,
        },
        "next_action": "Review these three generously detailed directions. They are 3 of 10 potential ideas, not a ranked top three, and they are starting hypotheses, not verified buyer demand.",
        "privacy": {"local_only": True, "external_writes": 0},
    }


def _revenue_resume_response(state_dir: Path) -> dict[str, Any] | None:
    revenue_path = state_dir / "revenue.json"
    if not revenue_path.exists() and not revenue_path.is_symlink():
        return None
    snapshot = RevenueState(revenue_path).snapshot()
    commitment = snapshot.get("commitment")
    if not isinstance(commitment, dict):
        return None
    offers = snapshot.get("offers", {})
    if offers:
        latest = next(reversed(offers.values()))
        offer = latest.get("offer") if isinstance(latest, dict) else None
        if isinstance(offer, dict):
            return {
                "schema_version": "1.0",
                "phase": "offer_preview",
                "status": "test_offer_prepared",
                "offer": offer,
                "paid_offer_live": False,
                "next_action": "Review these provisional test-only terms. No Checkout, charge, provider call, or market action has occurred.",
                "privacy": {"local_only": True, "external_writes": 0},
            }
    return {
        "schema_version": "1.0",
        "phase": "committed",
        "status": "path_confirmed",
        "commitment": commitment,
        "paid_offer_allowed": False,
        "next_action": "Review the exact managed-sprint terms before any test Checkout is prepared.",
        "privacy": {"local_only": True, "external_writes": 0},
    }


def startup_turn(state_dir: str | Path, request: dict[str, Any]) -> dict[str, Any]:
    """Execute one local `/startup` turn without external writes.

    Only the ``balance`` action performs a read-only network request (the
    Hermes Startup API wallet); every other action is fully local.
    """
    if not isinstance(request, dict) or set(request) - {"action", "answer", "question_id", "hypothesis_id", "evidence_budget", "stop_rule", "profile_id", "option", "installation_id"}:
        raise ValueError("startup request schema is invalid")
    action = request.get("action")
    onboarding_path = Path(state_dir) / "onboarding.json"

    if action == "start":
        existing = load_onboarding(onboarding_path)
        state = start_onboarding(onboarding_path)
        if state["next_question"] is None:
            revenue_response = _revenue_resume_response(Path(state_dir))
            if revenue_response is not None:
                return revenue_response
            return _completed_response(onboarding_path)
        return _incomplete_response(state, phase="new" if existing is None else "resuming")
    if action == "answer":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is None:
            raise ValueError("onboarding is not awaiting an answer")
        answer = request.get("answer")
        if not isinstance(answer, str):
            raise ValueError("an onboarding answer is required")
        state = answer_onboarding(onboarding_path, loaded["next_question"]["id"], answer)
        if state["next_question"] is not None:
            return _incomplete_response(state, phase="resuming")
        return _completed_response(onboarding_path)
    if action == "prefer_not_to_say":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is None:
            raise ValueError("onboarding is not awaiting an answer")
        state = answer_onboarding(onboarding_path, loaded["next_question"]["id"], "prefer_not_to_say")
        if state["next_question"] is not None:
            return _incomplete_response(state, phase="resuming")
        return _completed_response(onboarding_path)
    if action == "correct":
        if load_onboarding(onboarding_path) is None:
            raise ValueError("onboarding has not been started")
        question_id = request.get("question_id")
        answer = request.get("answer")
        if not isinstance(question_id, str) or not isinstance(answer, str):
            raise ValueError("question_id and corrected answer are required")
        state = answer_onboarding(onboarding_path, question_id, answer)
        if state["next_question"] is None:
            result = _completed_response(onboarding_path)
        else:
            result = _incomplete_response(state, phase="resuming")
        result["corrected_question_id"] = question_id
        return result
    if action == "inspect":
        state = load_onboarding(onboarding_path)
        if state is None:
            raise ValueError("onboarding has not been started")
        return {
            "schema_version": "1.0",
            "phase": "inspection",
            "status": "complete" if state["next_question"] is None else "incomplete",
            "answers": state["answers"],
            "next_question": state["next_question"],
            "privacy": {"local_only": True, "external_writes": 0},
            "next_action": "Correct an answer, delete local onboarding, or resume with the next question.",
        }
    if action == "delete":
        revenue_state = RevenueState(Path(state_dir) / "revenue.json")
        revenue_state.validate_deletable()
        validate_onboarding_deletable(onboarding_path)
        revenue_deleted = revenue_state.delete()
        onboarding_deleted = delete_onboarding(onboarding_path)
        deleted = onboarding_deleted or revenue_deleted
        return {
            "schema_version": "1.0",
            "phase": "new",
            "status": "deleted" if deleted else "already_absent",
            "paid_offer_allowed": False,
            "next_action": "Use /startup when you want to begin again.",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    if action == "confirm_path":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is not None:
            raise ValueError("completed onboarding is required before confirming a path")
        qualification = qualify_onboarding(onboarding_path)
        if qualification["qualification"] != "qualified":
            raise ValueError("qualified onboarding is required before confirming a path")
        opportunity_map = build_opportunity_map(qualification, loaded["answers"])
        hypothesis_id = request.get("hypothesis_id")
        hypothesis = next((item for item in opportunity_map["hypotheses"] if item["id"] == hypothesis_id), None)
        if hypothesis is None:
            raise ValueError("hypothesis is not in the current opportunity map")
        state = RevenueState(Path(state_dir) / "revenue.json")
        commitment = state.confirm_path(
            hypothesis_id,
            evidence_budget=request.get("evidence_budget"),
            stop_rule=request.get("stop_rule"),
        )
        return {
            "schema_version": "1.0",
            "phase": "committed",
            "status": "path_confirmed",
            "commitment": commitment,
            "guidance": build_startup_guidance(hypothesis, loaded["answers"]),
            "paid_offer_allowed": False,
            "next_action": "Review the exact managed-sprint terms before any test Checkout is prepared.",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    if action == "prepare_test_offer":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is not None:
            raise ValueError("completed onboarding is required before preparing an offer")
        qualification = qualify_onboarding(onboarding_path)
        state = RevenueState(Path(state_dir) / "revenue.json")
        commitment = state.snapshot().get("commitment")
        if not isinstance(commitment, dict):
            raise ValueError("a confirmed path is required before preparing an offer")
        profile_id = request.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip() or len(profile_id) > 128 or any(ord(character) < 33 or ord(character) > 126 for character in profile_id):
            raise ValueError("a bounded local profile id is required")
        offer = build_managed_sprint_offer(qualification, commitment, **TEST_OFFER_TERMS)
        state.save_prepared_offer(profile_id, offer)
        return {
            "schema_version": "1.0",
            "phase": "offer_preview",
            "status": "test_offer_prepared",
            "offer": offer,
            "paid_offer_live": False,
            "next_action": "Review these provisional test-only terms. No Checkout, charge, provider call, or market action has occurred.",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    if action == "make_card":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is not None:
            raise ValueError("completed onboarding is required before making a share card")
        qualification = qualify_onboarding(onboarding_path)
        if qualification["qualification"] != "qualified":
            raise ValueError("qualified onboarding is required before making a share card")
        share = _load_share_state(Path(state_dir))
        if share.get("declined"):
            return {
                "schema_version": "1.0",
                "phase": "complete",
                "status": "share_declined",
                "share_offer": {"milestone": _QUESTIONS_COMPLETE_MILESTONE, "declined": True, "copy": _SHARE_POPUP_COPY},
                "next_action": "You chose not to share this milestone. That is always final.",
                "privacy": {"local_only": True, "external_writes": 0},
            }
        option = request.get("option")
        if not isinstance(option, str) or option not in _QUESTION_COMPLETE_OPTIONS:
            raise ValueError("a safe share option is required")
        card_svg = render_flex_card(_QUESTIONS_COMPLETE_MILESTONE, custom=option)
        target = Path(state_dir) / _SHARE_CARD_FILE
        target.write_text(card_svg, encoding="utf-8")
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return {
            "schema_version": "1.0",
            "phase": "complete",
            "status": "share_card_ready",
            "card": {"milestone": _QUESTIONS_COMPLETE_MILESTONE, "option": option, "path": str(target)},
            "share_offer": {"milestone": _QUESTIONS_COMPLETE_MILESTONE, "options": list(_QUESTION_COMPLETE_OPTIONS), "declined": False, "copy": _SHARE_POPUP_COPY},
            "next_action": "The card is saved locally. Sharing it is your explicit choice.",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    if action == "decline_share":
        loaded = load_onboarding(onboarding_path)
        if loaded is None or loaded["next_question"] is not None:
            raise ValueError("completed onboarding is required before managing a share offer")
        qualification = qualify_onboarding(onboarding_path)
        if qualification["qualification"] != "qualified":
            raise ValueError("qualified onboarding is required before managing a share offer")
        _save_share_state(Path(state_dir), {"milestone": _QUESTIONS_COMPLETE_MILESTONE, "declined": True})
        return {
            "schema_version": "1.0",
            "phase": "complete",
            "status": "share_declined",
            "share_offer": {"milestone": _QUESTIONS_COMPLETE_MILESTONE, "declined": True, "copy": _SHARE_POPUP_COPY},
            "next_action": "You chose not to share this milestone. That is always final.",
            "privacy": {"local_only": True, "external_writes": 0},
        }
    if action == "balance":
        installation_id = request.get("installation_id")
        if not isinstance(installation_id, str) or len(installation_id) != 32 or any(character not in "0123456789abcdef" for character in installation_id):
            raise ValueError("a valid installation_id is required for a balance check")
        try:
            wallet = fetch_wallet_balance(api_base_url(), installation_id, state_dir=Path(state_dir))
        except WalletUnavailable as error:
            return {
                "schema_version": "1.0",
                "phase": "wallet",
                "status": "balance_unavailable",
                "reason": str(error),
                "next_action": "The balance could not be read right now; try again later. No number is shown rather than guessing.",
                "privacy": {"local_only": False, "external_writes": 0, "network_reads": 1},
            }
        available_microusd = wallet.get("available_microusd")
        if type(available_microusd) is not int or available_microusd < 0:
            return {
                "schema_version": "1.0",
                "phase": "wallet",
                "status": "balance_unavailable",
                "reason": "wallet_service_invalid_response",
                "next_action": "The balance could not be read right now; try again later. No number is shown rather than guessing.",
                "privacy": {"local_only": False, "external_writes": 0, "network_reads": 1},
            }
        return {
            "schema_version": "1.0",
            "phase": "wallet",
            "status": "balance_available",
            "balance": {
                "available_microusd": available_microusd,
                "available_usd": f"{available_microusd / 1_000_000:.2f}",
                "currency": wallet.get("currency", "usd"),
                "usd1_notice_pending": bool(wallet.get("usd1_notice_pending", False)),
            },
            "next_action": "This is the exact prepaid balance. It only changes when Hermes Startup runs approved paid work or a top-up completes.",
            "privacy": {"local_only": False, "external_writes": 0, "network_reads": 1},
        }
    raise ValueError("unsupported startup action")
