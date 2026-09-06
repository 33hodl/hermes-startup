# Hermes Startup

Make your first genuine dollar online using Hermes Agent.

Hermes Startup is a local-first Hermes skill. It asks a few focused questions, gives you evidence-labeled ideas grounded in what you know and can reach, helps you choose a problem worth solving, and prepares the smallest reversible test.

## Install

```bash
hermes skills install https://hermesstartup.com/skill/SKILL.md
```

Then use:

```text
/startup
```

Hermes exposes installed skills as dynamic slash commands.

## What this repository contains

- The portable `startup` skill
- A bounded JSON/stdin adapter
- Local onboarding and state handling
- Opportunity, offer-preview, entitlement, and exact-approval contracts
- A deterministic zero-network local runtime

## Safety boundary

The free journey is local by default. It does not create Checkout, charge a card, contact a provider or buyer, publish, deploy, or make another external write. Any consequential action requires an exact target-and-content preview and explicit approval.

This public repository intentionally excludes the managed hosted service, payment and community infrastructure, deployment configuration, private operational reports, credentials, and provider-specific operations.

## Run locally

```bash
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/hermes-startup"
printf '%s' '{"action":"start"}' | python3 scripts/startup_turn.py --state-dir "$state_dir"
```

The adapter accepts exactly one bounded JSON object through stdin and emits one JSON response.

## Live product

Hermes Startup is live at [hermesstartup.com](https://hermesstartup.com). The free
path: 10 private questions answered inside your Hermes Agent, and all 10
demand-checked ideas back, ranked with the reason why. The optional paid path: a
one-time **US$10** prepaid continuation that builds and runs the business you
choose. One balance funds 1,000+ API tools from 20+ providers; no subscription,
no renewal, auto top-up only when you turn it on, balance never expires, US$1
low-balance alert. Checkout is live via Stripe. Every action and spend requires
your explicit approval. No income, customer, or outcome guarantee.

- Agent-facing brief: https://hermesstartup.com/for-agents.md
- Step-by-step workflows: https://hermesstartup.com/workflows
- Business profile (UCP): https://hermesstartup.com/.well-known/ucp

## Status

Open-source skill export (MIT), synced from the live product.

## License

MIT. See [LICENSE](LICENSE).

Hermes Startup is an independent product for Hermes Agent users. It is not affiliated with or endorsed by Nous Research.
