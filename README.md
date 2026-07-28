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

## Status

This is an unpublished private pilot. The optional founding offer is proposed as one one-time US$10 payment for one bounded validation sprint. Checkout is not live. No subscription, renewal, automatic top-up, or earnings guarantee.

## License

MIT. See [LICENSE](LICENSE).

Hermes Startup is an independent product for Hermes Agent users. It is not affiliated with or endorsed by Nous Research.
