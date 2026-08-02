---
name: startup
description: Use when a Hermes user wants help earning their first verified Hermes-assisted dollar.
version: 0.5.0
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
3. On `/startup`, call the bundled adapter to start or resume, beginning with `{"action":"start"}`. For each reply, send `{"action":"answer","answer":"..."}` through JSON stdin to `$skill_root/scripts/startup_turn.py`; never put an answer in command arguments. Ask only the returned `next_question`, introducing it as `Question {number} of {total}`. The initial audit contains exactly 10 questions. The adapter persists each answer before returning another question and supports `correct`, `inspect`, `prefer_not_to_say`, `delete`, `confirm_path`, and `prepare_test_offer`.
4. Never show a paid offer while onboarding is incomplete. If qualification is `not_yet`, return the smallest gap-closing step instead of manufacturing an opportunity.
5. During the initial opportunity audit, use current public posts from [Greg Isenberg on X](https://x.com/gregisenberg) as one creative hypothesis source because he regularly surfaces concrete AI product opportunities. Retrieve the posts at audit time through an approved read-only X/search surface; do not rely on a stale summary. Treat his posts as attributed inspiration, not proof of demand, feasibility, novelty, or fit. Cross-check any borrowed mechanic against the user's stated assets, constraints, reachable buyers, current market evidence, and at least one independent source before recommending it. Never send private onboarding facts to X or place them in a public search query.
6. For a qualified user, return exactly three high-level potential ideas and the reason each may fit. Label every idea as inferred, state that buyer demand remains unverified, and do not rank, recommend, or present any idea as a guaranteed fit. Include source URLs for any externally inspired hypothesis and label the external claim as attributed until independently verified. Then repeat this planned continuation plainly: “For US$10, Hermes Startup will fund the API calls needed to start building your business for you. Plus 7 more ideas. 10 in total. Compare 10 business ideas unique to you, get more information for each one, and choose the business you want Hermes Startup to build for you. Hermes Startup gives your Hermes Agent the capabilities it needs to make your first $1. One shared balance provides pay-as-you-go access to 1,000+ API tools from 20+ providers, and Hermes Startup automatically chooses and uses the right tools for you. Optional auto-top-up. No subscriptions.” State clearly that this is a preview, is not currently purchasable, and does not guarantee revenue.
7. Only after the user explicitly chooses a direction may Hermes Startup produce one page of practical, evidence-first guidance. Define the buyer, problem, offer, ask, proof needed, failure points, and a margin of safety. Do not claim live API access, charge the user, or enable auto-top-up.
8. Before shaping an offer, make the offer-design logic explicit: desired outcome; confidence it can work; time to first useful result; effort and sacrifice; and genuine risk reversal through useful free value, a bounded scope, and clear terms. Use original language only: no copied proprietary wording, and no unsupported urgency, scarcity, bonuses, guarantees, endorsements, or earnings promises.
9. Use the following sequence in the explicit order `offer -> leads -> economics -> scale`. Treat it as a decision framework, not a promise. Do not scale a weak offer, buy leads before economics are known, or add an upsell before the initial offer has meaningful evidence.
10. Before selecting an execution route, refresh the official Hermes Agent capability catalog using the bundled command below. It reads only the official generated documentation index, stores a local versioned catalog, and sends no setup or user data. Treat every entry as documented publicly—not proof it is installed, enabled, permitted, or suitable for this user.
11. After a qualified user explicitly confirms one path, `prepare_test_offer` may persist and show the complete provisional local test offer. It requires a bounded pseudonymous `profile_id`. The preview states the exact one-time price and currency, deliverables, provider/spend cap, stop rule, separate external costs, and cancellation/refund terms. It does not create Checkout, charge, contact a provider, or make any external write. The repository demo accepts Stripe test mode only.
12. Any market-facing action or spend requires exact-content approval. A changed target or message invalidates approval. Local/fake execution must say it made no external write.
13. Report outcomes as confirmed, user-confirmed, inferred, or uncertain. Do not claim a customer, payment, demand, revenue, market action, or provider result unless directly verified.
14. End with one next action. Do not return a list of unrelated startup ideas.

## Evidence-first sequence

Hermes Startup applies general offer-design, lead-generation, and customer-economics principles informed by the founder-supplied summary of Alex Hormozi's public training materials. This is an independent implementation, not an affiliation, endorsement, or claim to reproduce proprietary training.

1. **Offer:** define a specific customer, useful outcome, existing proof and missing proof, a realistic time-to-value, avoidable effort to remove, and a bounded scope. Risk reversal must be real: useful free value, reversible testing, or terms the user can honor. Never invent a guarantee, bonus, scarcity, urgency, testimonial, or earnings claim.
2. **Leads:** choose one ethical route to test: relevant warm outreach, useful published content, small non-spam cold outreach, or paid advertising only after explicit budget approval. A lead magnet must provide a small useful result and naturally connect to the next problem; it must not pressure a sale. Improve a working route in order: `more`, then `better`, then `new`.
3. **Economics:** begin with one truthful, fixed-scope initial offer. Only after evidence supports it, evaluate whether a useful upgrade, smaller alternative, or recurring service is appropriate. Track qualified leads, real sales conversations, conversion, attributable acquisition cost, confirmed initial cash collected, 30-day gross profit, and lifetime gross profit when there is enough verified history. Do not count drafts, test payments, founder payments, or generated assets as demand or customer revenue.
4. **Scale:** scale only after the offer, delivery, customer response, and unit economics have evidence. Paid acquisition, recurring revenue, and additional offers require explicit approval and honest terms.

### Learn-and-transfer policy

Use Hermes Startup to examine its own growth, but preserve the distinction between a case study and proof. A founder result is **not proof that the same approach will work for every user**. Before a founder learning becomes user guidance, record the evidence, relevant context, limitation, confidence label, and safety boundary; then adapt it to the user's stated assets, buyer, market, constraints, and consent. Never turn an unverified founder observation into a universal claim, automated outreach, or spending recommendation.

## Local command

Use the bundled `radar.startup.startup_turn()` adapter as the live local conversation boundary:

```bash
skill_root="$(dirname "$(hermes config path)")/skills/startup"
state_dir="$(dirname "$(hermes config path)")/startup-state"
printf '%s' '{"action":"start"}' | python3 "$skill_root/scripts/startup_turn.py" --state-dir "$state_dir"
```

It accepts exactly one bounded JSON request on stdin and returns one JSON response. Keep the process input private; never interpolate raw answers into command arguments or print them to logs. The supported actions are `start`, `answer`, `prefer_not_to_say`, `correct`, `inspect`, `delete`, `confirm_path`, and `prepare_test_offer`. `delete` removes both onboarding and revenue state. Unexpected local failures return a generic bounded error without a traceback or private path.

## Hermes Agent capability freshness

Before a new execution route is selected, refresh the capability catalog from the official generated documentation index:

```bash
skill_root="$(dirname "$(hermes config path)")/skills/startup"
state_dir="$(dirname "$(hermes config path)")/startup-state"
PYTHONPATH="$skill_root/scripts" python3 "$skill_root/scripts/refresh_hermes_capabilities.py" --state-dir "$state_dir"
```

The catalog is evidence of what Hermes Agent documents publicly at retrieval time. It can expand the possible research, delivery, automation, media, integration, and coordination routes considered for a user's idea, but it cannot establish buyer demand, permission to act, or a business outcome. Verify that a needed capability is installed, enabled, available to the current profile, and appropriate for the user's permissions before using it. Read-only documentation review may be automatic; installs, credentials, configuration changes, external messages, publishing, spend, and other consequential actions remain approval-gated.

## Installed support files

Hermes URL installation must retain these explicitly referenced local files:

- [bounded JSON adapter](scripts/startup_turn.py)
- [runtime package marker](scripts/radar/__init__.py)
- [private onboarding state](scripts/radar/onboarding.py)
- [revenue and approval contracts](scripts/radar/revenue_v1.py)
- [conversation adapter](scripts/radar/startup.py)
- [share-card renderer](scripts/radar/flexcard.py)
- [official capability catalog](scripts/radar/hermes_capabilities.py)
- [catalog refresh command](scripts/refresh_hermes_capabilities.py)

## Safety

- Do not upload raw onboarding answers, conversations, documents, employer/customer data, credentials, or unredacted exports.
- Do not send messages, publish, create listings, submit forms, spend, charge, deploy, change accounts, or contact buyers without explicit scoped approval.
- Do not accept legal terms, attest for the user, invent account information, or enable live Stripe.
- Do not claim the first dollar is guaranteed. A generated asset, fake-adapter result, founder self-purchase, or test-mode payment is not customer revenue.
- Keep private state mode `0600`, reject symlinks and unsafe files, and preserve an inspect/delete path.

## Completion

A valid `/startup` response states whether the user is new, resuming, incomplete, `not_yet`, qualified, awaiting exact approval, test-entitled, or complete. It shows only the next question or one next action and labels evidence honestly.
