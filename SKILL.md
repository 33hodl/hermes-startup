---
name: startup
description: Use when a Hermes Agent user wants help earning their first verified Hermes Agent-assisted dollar.
version: 0.7.0
author: Hermes Startup contributors
license: MIT
metadata:
  hermes:
    tags: [startup, first-dollar, onboarding, validation, revenue]
---

# Hermes Startup

## Purpose

Help the user move from an honest local profile to one evidence-backed opportunity, one bounded demand test, and eventually one genuine non-founder customer payment materially assisted by Hermes Agent.

Hermes Agent documents that installed skills are exposed as dynamic slash commands. Installing this skill therefore makes `/startup` the supported native entry point without patching Hermes Agent core. Natural-language requests such as “help me make my first dollar with Hermes Agent” use the same workflow. `/radar` remains a legacy setup-audit path.

## Workflow

1. Resolve this installed skill without assuming a user, profile, or operating-system home: `skill_root="$(dirname "$(hermes config path)")/skills/startup"`. Confirm `$skill_root/scripts/startup_turn.py` exists before running it. If it does not, explain that the installation is incomplete; do not reconstruct missing files.
2. Use `state_dir="$(dirname "$(hermes config path)")/startup-state"` for private local state. The adapter creates `onboarding.json` and `revenue.json` there with restrictive permissions, plus `share.json` and a rendered `share-questions-complete.svg` when the user chooses the optional local share card. Raw answers stay local.
3. On `/startup`, call the bundled adapter to start or resume, beginning with `{"action":"start"}`. For each reply, send `{"action":"answer","answer":"..."}` through JSON stdin to `$skill_root/scripts/startup_turn.py`; never put an answer in command arguments. Ask only the returned `next_question`, introducing it as `Question {number} of {total}`, and follow the onboarding quality bar below. Make each question feel genuinely understood: briefly connect it to what the user has already shared (their goal, constraints, or past attempts) before asking, and never read stored answers back verbatim into public text. The initial audit contains exactly 10 high-quality, personalized questions. The adapter persists each answer before returning another question and supports `correct`, `inspect`, `prefer_not_to_say`, `delete`, `confirm_path`, `prepare_test_offer`, `make_card`, `decline_share`, and `balance`.
4. Never show a paid offer while onboarding is incomplete. If qualification is `not_yet`, return the smallest gap-closing step instead of manufacturing an opportunity.
5. During the initial opportunity audit, use current public posts from [Greg Isenberg on X](https://x.com/gregisenberg) as one creative hypothesis source because he regularly surfaces concrete AI product opportunities. Retrieve the posts at audit time through an approved read-only X/search surface; do not rely on a stale summary. Treat his posts as attributed inspiration, not proof of demand, feasibility, novelty, or fit. Cross-check any borrowed mechanic against the user's stated assets, constraints, reachable buyers, current market evidence, and at least one independent source before recommending it. Never send private onboarding facts to X or place them in a public search query.
6. For a qualified user, return exactly three generous, detailed potential ideas — framed clearly as **3 of 10 potential ideas, not "the top three"**. For every one of the three, explain each of: (a) **what the idea is** in plain language; (b) **why it was chosen for this user** specifically, tied to something they said; (c) **how Hermes Startup would execute on it** — the concrete first steps it would take; (d) **its realistic potential**, stated without an income guarantee; (e) **a realistic timeframe** to the first useful result or test; and (f) anything else helpful for that person, such as the first proof they would need. Label every idea as inferred, state that buyer demand remains unverified, and explicitly say these are a sample from a larger set — not a ranking and not the guaranteed best three. Include source URLs for any externally inspired hypothesis and label the external claim as attributed until independently verified. Do not present any idea as a guaranteed fit, and do not withhold detail to push the sale — the free tier is meant to be genuinely useful on its own. Then repeat this planned continuation plainly: “A money-making business, built for you. Plus 7 more ideas, so you get all 10 — every one of them graded and ranked, with the reason why, so you can compare the full set and choose. Hermes Startup gives your Hermes Agent the capabilities it needs to make your first $1. One shared balance provides pay-as-you-go access to 1,000+ API tools from 20+ providers, and Hermes Startup automatically chooses and uses the right tools for you. Optional auto-top-up. No subscriptions.” State clearly that this is a preview, is not currently purchasable, and does not guarantee revenue. When the completed response carries a `share_offer`, present it once as an optional, purely local share card — the options are safe, generic custom lines that never contain the user's answers or an idea title. `make_card` renders the card locally (mode 0600); `decline_share` records their choice. Sharing the card is always the user's explicit act; never post, upload, or attach it yourself.
7. Only after the user explicitly chooses a direction may Hermes Startup produce one page of practical, evidence-first guidance. Define the buyer, problem, offer, ask, proof needed, failure points, and a margin of safety. Derive it by backward induction (see the Backward induction section): write the terminal end state in one sentence, then walk backward asking "What must be true one step before?" down to today. Do not claim live API access, charge the user, or enable auto-top-up. When the paid tier later unlocks the full set, present the ideas as a ranking with plain reasons — never as a blind numbered list — and grade each one on fit, whether it is a problem the user could care about solving, and overall offer strength. Explain the ranking honestly in plain language; never attribute the grading method to any named source or framework when describing it to the user.
8. Before shaping an offer, make the offer-design logic explicit: desired outcome; confidence it can work; time to first useful result; effort and sacrifice; and genuine risk reversal through useful free value, a bounded scope, and clear terms. Use original language only: no copied proprietary wording, and no unsupported urgency, scarcity, bonuses, guarantees, endorsements, or earnings promises.
9. Use the following sequence in the explicit order `offer -> leads -> economics -> scale`. Treat it as a decision framework, not a promise. Do not scale a weak offer, buy leads before economics are known, or add an upsell before the initial offer has meaningful evidence.
10. Before selecting an execution route, refresh the official Hermes Agent capability catalog using the bundled command below. It reads only the official generated documentation index, stores a local versioned catalog, and sends no setup or user data. Treat every entry as documented publicly—not proof it is installed, enabled, permitted, or suitable for this user.
11. After a qualified user explicitly confirms one path, `prepare_test_offer` may persist and show the complete provisional local test offer. It requires a bounded pseudonymous `profile_id`. The preview states the exact one-time price and currency, deliverables, provider/spend cap, stop rule, separate external costs, and cancellation/refund terms. It does not create Checkout, charge, contact a provider, or make any external write. The repository demo accepts Stripe test mode only.
12. Any market-facing action or spend requires exact-content approval. A changed target or message invalidates approval. Local/fake execution must say it made no external write.
13. Report outcomes as confirmed, user-confirmed, inferred, or uncertain. Do not claim a customer, payment, demand, revenue, market action, or provider result unless directly verified.
14. End with one next action: the earliest unmet precondition on the backward-induction chain, not the most attractive activity. Do not return a list of unrelated startup ideas.

## Backward induction (structural planning rule)

Adopted 2026-08-08 from @incentivising on backward induction:
https://x.com/incentivising/status/2085434985389969532 (8,882 likes / 1,263 reposts
at retrieval; general game-theory advice, not Hermes-specific).

- Every plan/map starts by writing the terminal end state in one sentence — for example,
  "a non-founder customer pays US$10, receives the bounded sprint, and confirms the
  outcome with verifiable evidence" — then walks backward asking "What must be true one
  step before?" down to today.
- The one next action is the earliest unmet precondition on that chain. Closing an unmet
  precondition beats adding decoration.
- Feature admissibility test: "Is this a precondition of the end state, or decoration?"
  Decoration is sequenced later. Agent-discoverability and commerce surfaces (llms.txt,
  structured metadata, agent-to-service flows) are preconditions of the agent-first scale
  end state, not of the first human $1; human messaging keeps leading with the first $1.
- Evidence rule unchanged: a claim (site live, payment, outcome) is verified from its
  source, never inferred.

## Onboarding quality bar

The onboarding questions decide whether a user keeps going, so ask them like a careful human, not a script. Before each question:

- Read the question once, then say it in your own plain words to that person, without jargon, without adding pressure, and without reordering or merging questions.
- Tie the question to what they already told you — their goal, constraints, or past attempt — with one short connecting sentence, then ask. Never read their stored answer back verbatim; paraphrase in your own words if you reference it at all.
- Ask exactly one question per turn. If they answer a different question or drift, gently bring the thread back before storing their answer.
- Keep each exchange short and concrete. If they give a vague answer, ask one focused follow-up to get the specifics the question is really after; never store an empty or off-topic answer.
- If they want to skip a question, use `prefer_not_to_say` without pushing back or implying it disqualifies them. Skipping is legitimate and the audit adapts.
- Never ask anything not in the audit, never show a paid offer during onboarding, and never imply their answers are being graded against other people.

The adapter returns the next question in `next_question` with its `number` and `total`. Introduce it as `Question {number} of {total}` so the user always sees how far they are through the audit.

## Evidence-first sequence

Hermes Startup applies general offer-design, lead-generation, and customer-economics principles from widely-available public business education. This is an independent, original implementation — not affiliated with, endorsed by, or a reproduction of any specific author's or program's proprietary material. Public explanations of how ideas are graded and ranked are always given in plain language and never attributed to a named source or framework.

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

It accepts exactly one bounded JSON request on stdin and returns one JSON response. Keep the process input private; never interpolate raw answers into command arguments or print them to logs. The supported actions are `start`, `answer`, `prefer_not_to_say`, `correct`, `inspect`, `delete`, `confirm_path`, `prepare_test_offer`, `make_card`, `decline_share`, and `balance`. `delete` removes both onboarding and revenue state; the optional share card and its `share.json` state are left untouched (they hold no answer text and can be removed manually). Unexpected local failures return a generic bounded error without a traceback or private path.

To answer "what is my balance?" send `{"action":"balance","installation_id":"<32-hex-anonymous-installation-id>"}`. The adapter reads the exact prepaid balance from the Hermes Startup API (`/v1/activate` then `GET /v1/wallet`) using the same anonymous installation id the purchase flow binds to. It is strictly read-only — it never charges, spends, or writes. If the API is unreachable the adapter returns `balance_unavailable` with a reason and NO number, never a guess. The base URL comes from `HERMES_STARTUP_API_BASE_URL` (default `https://api.hermesstartup.com`; loopback hosts are allowed for local testing only, everything else must be https).

## Hermes Agent capability freshness

Before a new execution route is selected, refresh the capability catalog from the official generated documentation index:

```bash
skill_root="$(dirname "$(hermes config path)")/skills/startup"
state_dir="$(dirname "$(hermes config path)")/startup-state"
PYTHONPATH="$skill_root/scripts" python3 "$skill_root/scripts/refresh_hermes_capabilities.py" --state-dir "$state_dir"
```

The catalog is evidence of what Hermes Agent documents publicly at retrieval time. It can expand the possible research, delivery, automation, media, integration, and coordination routes considered for a user's idea, but it cannot establish buyer demand, permission to act, or a business outcome. Verify that a needed capability is installed, enabled, available to the current profile, and appropriate for the user's permissions before using it. Read-only documentation review may be automatic; installs, credentials, configuration changes, external messages, publishing, spend, and other consequential actions remain approval-gated.

## Getting paid: Stripe setup (API and MCP)

When a user picks a direction that ends in collecting payment, guide them to connect their own Stripe account so their customers can pay them. Two complementary paths, both starting in test mode. The MCP path is fastest for agent-assisted operations; the API path is for the user's own checkout page or service.

1. **Stripe MCP (agent-operated).** The user creates a free Stripe account at stripe.com. Add the official Stripe MCP with `hermes mcp add stripe --url https://mcp.stripe.com` (or the desktop consent card). The user completes the Stripe login and 2FA in their own browser; never paste authorization codes or secrets into chat. Verify the connection with `hermes mcp test stripe` and the account-info tool, and confirm the account name before any write. Keep money-moving tools (refunds, payouts, Treasury) disabled by default and confirmation enabled. Read-only checks may be automatic; charges, refunds, and other writes need explicit approval.
2. **Stripe API (product runtime).** In Stripe Dashboard → Developers → API keys → create a **restricted key** starting from zero permissions, named for the service (for example `my-product-checkout`). Typical one-time Checkout baseline: Checkout Sessions write; Products and Prices read; Customers write only if the app creates customers. Keep Refunds, Balance, Payouts, and Disputes at none. Store the key outside chat and version control in a root-owned `0600` file; report presence and mode only, never the value. Collect payment with Stripe-hosted Checkout, never with card data in the user's app. Create an Account webhook endpoint subscribing only to `checkout.session.completed`, verify the raw body signature with the per-endpoint signing secret, and handle events idempotently. Test end to end in test mode (test card `4242 4242 4242 4242 4242`), then go live only after the test path, webhook verification, and rollback/refund policy are proven, and only with the user's explicit approval for live mode.
3. **Prepaid balance pattern (collect once, spend per job).** For work delivered over time, collect into a prepaid balance instead of invoicing per job: one payment up front, every job debits from the balance, an alert when the balance runs low, and manual top-ups. Auto-top-up is a deliberate opt-in, never a default, and a failed charge is never retried automatically. The founder runs this exact model on Hermes Startup: one-time payment, manual top-ups, a low-balance alert, opt-in auto-top-up only.

Fast path: account (about 5 minutes) → MCP in test mode → one test payment → switch MCP to live → restricted key plus hosted Checkout plus signed webhook → live payment. Card data never enters chat. The Stripe account, keys, and mode remain the user's own; Hermes Startup never touches them without explicit approval.

## Know the moment you get paid: payment alerts

A payment that lands silently is a payment you cannot confirm, thank, or chase. The founder gets a phone message the instant a live payment clears, and again when one fails. Offer the same to the user once their direction can take money.

1. Create a private Telegram bot (or any messaging bot the user already has). Keep the bot token in a root-owned `0600` env file; never paste it into chat.
2. In the payment service's webhook handler, after a verified payment-completed event, send one short message with the amount and order id. Send a second message when a payment fails or a signature check fails.
3. Test with a real test-mode payment before going live. The alert doubles as proof that the webhook path works end to end.

Fast path: bot (10 minutes) → success and failure messages → one test payment → live.

Honest framing: the alert confirms a payment happened. It does not make the next sale.

## Watch your site without watching it

A site that dies quietly loses sales. The founder's live payment service has been checked every 5 minutes since launch, and it messages only on failure or recovery. Silence means healthy. That is the whole trick.

1. Set one recurring job that fetches the site's health URL, or any public page, and checks for a sane response.
2. Message only when a check fails, and once when it recovers. Never message on success; success is the default state, and noise trains people to ignore the alert.
3. Keep the check cheap: a plain HTTP GET, no browser, no login. A 5-minute cadence costs almost nothing.

Fast path: one script plus one recurring job (about 15 minutes), then forget it.

## Sell on X: what the founder verified

The founder sells Hermes Startup on X. The numbers below come from X's open-sourced ranking code, checked directly on 2026-08-13.

- A copy-link share carries roughly 40 times the weight of a like. A reply carries about 10 times a like. A report is the single worst signal there is.
- Original posts from accounts that follow you back get an extra boost on top of the reply weight. Replies and reposts do not.
- A post's relevance window is about 80 hours. Fresh posts rank better, and a post's useful life is days, not weeks.

The doctrine the founder runs: one post a week, link in the bio and never in the body, share the post with the share or copy-link button, answer every reply, never bait engagement, and one consistent cover style every time (1500x600 on the founder's posts).

Honest framing: these are public ranking weights at a point in time. They describe how the feed scores signals. They are not a promise of reach or sales.

## Turn Hermes Agent releases into your edge

Every Hermes Agent release ships new capabilities. The founder reads each release, asks what it means for Hermes Startup, and turns the useful part into one plain-language post. Platform updates are free marketing material, and they keep a business current without inventing content.

1. When Hermes Agent updates, read the release notes and pick the one or two changes that matter for the user's direction.
2. Ask the same question each time: what does this change make possible for a customer, and what is it worth? Write the answer in plain words, one post.
3. Post only with exact-content approval. Keep a short record of what was posted and when.

Fast path: one weekly recurring job that fetches the release notes, drafts one post, and waits for approval.

## Build a team of bots

One bot per job beats one bot doing every job. The founder runs separate bots for finding ideas, checking the market, building, and answering customers. Each bot is a separate profile with its own memory, and they hand work to each other with an @mention. A shared group chat shows the work happening.

1. Split the user's direction into jobs: find the idea, check demand, build the offer, answer buyers. Give each job its own bot profile and memory.
2. Hand off with an @mention in a shared chat. The receiving bot picks up the message and reports back.
3. Run the watching bots on a fast, low-cost model and keep the strong model for writing and building. The founder runs his whole bot team on a fast, low-cost model. The value is separation, not model variety, and that is how a small prepaid balance goes far.

Honest framing: a team of bots organizes the work. It does not guarantee customers.

## Save every repeated workflow as a skill

Any workflow the user does twice should become a skill: a named file with the exact steps, saved where the agent can load it. The founder runs Hermes Startup this way, and this skill is the proof. Skills turn repeated work into one-prompt work.

1. After any task that took several steps, save the steps as a skill with a clear trigger description, the words the user will type next time.
2. Update the skill when steps change or a pitfall shows up. A skill that is not maintained becomes a liability.
3. Count the saved time as the return on the writing time.

Fast path: name it, write the steps, save it. Next time it is one prompt.

## Installed support files

Hermes Agent URL installation must retain these explicitly referenced local files:

- [bounded JSON adapter](scripts/startup_turn.py)
- [runtime package marker](scripts/radar/__init__.py)
- [private onboarding state](scripts/radar/onboarding.py)
- [revenue and approval contracts](scripts/radar/revenue_v1.py)
- [conversation adapter](scripts/radar/startup.py)
- [share-card renderer](scripts/radar/flexcard.py)
- [read-only wallet client](scripts/radar/wallet.py)
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
