---
name: startup
description: Use when a Hermes user wants help earning their first verified Hermes-assisted dollar.
version: 0.3.0
author: Hermes Startup contributors
license: MIT
metadata:
  hermes:
    tags: [startup, first-dollar, onboarding, validation, revenue]
---

# Hermes Startup

## Purpose

Help the user move from an honest local profile to one evidence-backed opportunity, one bounded demand test, and eventually one genuine non-founder customer payment materially assisted by Hermes.

Hermes documents that installed skills are exposed as dynamic slash commands. Installing this skill therefore makes `/startup` the supported native entry point without patching Hermes core. Natural-language requests such as “help me make my first dollar with Hermes” use the same workflow. `/radar` remains a legacy setup-audit path.

## Workflow

1. Resolve this installed skill without assuming a user, profile, or operating-system home: `skill_root="$(dirname "$(hermes config path)")/skills/startup"`. Confirm `$skill_root/scripts/startup_turn.py` exists before running it. If it does not, explain that the installation is incomplete; do not reconstruct missing files.
2. Use `state_dir="$(dirname "$(hermes config path)")/startup-state"` for private local state. The adapter creates `onboarding.json` and `revenue.json` there with restrictive permissions. Raw answers stay local.
3. On `/startup`, call the bundled adapter to start or resume, beginning with `{"action":"start"}`. For each reply, send `{"action":"answer","answer":"..."}` through JSON stdin to `$skill_root/scripts/startup_turn.py`; never put an answer in command arguments. Ask only the returned `next_question`. The adapter persists each answer before returning another question and supports `correct`, `inspect`, `prefer_not_to_say`, `delete`, `confirm_path`, and `prepare_test_offer`.
4. Never show a paid offer while onboarding is incomplete. If qualification is `not_yet`, return the smallest gap-closing step instead of manufacturing an opportunity.
5. For a qualified user, create one bounded map with one recommended opportunity, two alternatives, rejected categories, assumptions, evidence labels, uncertainty, cost/effort, and one next action.
6. Build the one-page First Dollar Map with the verified **DSSS + CaFE** framework: Deconstruction, Selection, Sequencing, Stakes, Compression, Frequency, and Encoding. Include failure points, a margin of safety, and the mnemonic `Buyer -> Problem -> Offer -> Ask -> Proof`.
7. After a qualified user explicitly confirms one path, `prepare_test_offer` may persist and show the complete provisional local test offer. It requires a bounded pseudonymous `profile_id`. The preview states the exact one-time price and currency, deliverables, provider/spend cap, stop rule, separate external costs, and cancellation/refund terms. It does not create Checkout, charge, contact a provider, or make any external write. The repository demo accepts Stripe test mode only.
8. Any market-facing action or spend requires exact-content approval. A changed target or message invalidates approval. Local/fake execution must say it made no external write.
9. Report outcomes as confirmed, user-confirmed, inferred, or uncertain. Do not claim a customer, payment, demand, revenue, market action, or provider result unless directly verified.
10. End with one next action. Do not return a list of unrelated startup ideas.

## Local command

Use the bundled `radar.startup.startup_turn()` adapter as the live local conversation boundary:

```bash
skill_root="$(dirname "$(hermes config path)")/skills/startup"
state_dir="$(dirname "$(hermes config path)")/startup-state"
printf '%s' '{"action":"start"}' | python3 "$skill_root/scripts/startup_turn.py" --state-dir "$state_dir"
```

It accepts exactly one bounded JSON request on stdin and returns one JSON response. Keep the process input private; never interpolate raw answers into command arguments or print them to logs. The supported actions are `start`, `answer`, `prefer_not_to_say`, `correct`, `inspect`, `delete`, `confirm_path`, and `prepare_test_offer`. `delete` removes both onboarding and revenue state. Unexpected local failures return a generic bounded error without a traceback or private path.

## Installed support files

Hermes URL installation must retain these explicitly referenced local files:

- [bounded JSON adapter](scripts/startup_turn.py)
- [runtime package marker](scripts/radar/__init__.py)
- [private onboarding state](scripts/radar/onboarding.py)
- [revenue and approval contracts](scripts/radar/revenue_v1.py)
- [conversation adapter](scripts/radar/startup.py)

## Safety

- Do not upload raw onboarding answers, conversations, documents, employer/customer data, credentials, or unredacted exports.
- Do not send messages, publish, create listings, submit forms, spend, charge, deploy, change accounts, or contact buyers without explicit scoped approval.
- Do not accept legal terms, attest for the user, invent account information, or enable live Stripe.
- Do not claim the first dollar is guaranteed. A generated asset, fake-adapter result, founder self-purchase, or test-mode payment is not customer revenue.
- Keep private state mode `0600`, reject symlinks and unsafe files, and preserve an inspect/delete path.

## Completion

A valid `/startup` response states whether the user is new, resuming, incomplete, `not_yet`, qualified, awaiting exact approval, test-entitled, or complete. It shows only the next question or one next action and labels evidence honestly.
