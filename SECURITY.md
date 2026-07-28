# Security

## Report a vulnerability

Do not include credentials, private conversations, customer data, employer data, payment details, or unredacted local state in a report. Until a public security contact is approved, do not send sensitive vulnerability details through public issues.

## Local-first boundary

Hermes Startup stores onboarding state locally with restrictive file permissions, rejects unsafe state paths, and accepts bounded JSON through stdin so private answers do not need to appear in command arguments. Market-facing actions require exact-content approval.

## Public-repository boundary

This repository does not contain hosted payment/control-plane code, production infrastructure, private operational reports, secrets, or provider credentials. Do not submit those materials in issues or pull requests.

## Launch status

Checkout, hosted jobs, and community admission are not public. Test-mode or fake-provider behavior must not be represented as production behavior.
