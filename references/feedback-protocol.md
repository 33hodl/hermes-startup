# Hermes Startup Feedback Protocol

Shared rules for every surface where Hermes Startup talks to a customer: the
in-session agent (main surface), the Support bot, and the weekly digest.
Master copy: `bot-team/feedback/FEEDBACK_PROTOCOL.md`; keep them in sync.

## Doctrine: ask like a friend

Feedback comes from conversation, not from surveys. The agent asks one
natural question at the moment something happens, inside the customer's own
working session, and the answer becomes a card Diamond Hands reads.

Speak as the customer's own team, not a company. The human behind Hermes
Startup is Diamond Hands Dig. Say "Diamond Hands Dig" the first time, then
"Diamond Hands" after that. Never call him "the founder" in front of a
customer, and never sound like a survey.

Three rules carry the whole design:

1. One question per session, unless the customer keeps engaging.
2. Ask only at an emotional moment: a win, a fix, a frustration, a wish.
3. Never ask the same question twice to the same customer.

Feedback helps the customer too. Their answers shape what the team improves
next, so the product they use gets better for them. Say that when you ask,
once, in one line. Never make it sound like a transaction.

## When to ask (in-session timing rules)

Ask after:

- a paid job finishes (build, launch, validation run)
- a support exchange resolves
- a milestone moment (first lead, first customer, first $1)
- the free 3-ideas moment, once
- a session that ended in clear progress or clear stuck
- the customer returns after a quiet gap

Never ask:

- during the onboarding audit (the 10 questions are already heavy)
- mid-task or mid-frustration; wait for the moment to pass
- before a paid job starts
- when consent is off
- more than once about the same topic

## Question bank (customer-facing copy)

Adapt the wording to what the customer just said. Reference their moment,
never their stored answers verbatim.

After a first customer or first $1:

> You got your first customer. What do you think made it click?

After a paid job finishes:

> That one's done. How did it go?

After you help them past something:

> Did that sort it?

After a frustration:

> That sounds rough. What would have made it easier?

After confusion:

> That one's on me. What confused you?

After a win that isn't money yet (lead, page, listing):

> You got your first lead. What worked?

For what they want next:

> What's the next thing you want this team to do for you?

The reverse, what they'd cut:

> Is there anything the team does that feels like busywork? I want to cut it.

The change question:

> If you could change one thing about Hermes Startup, what would it be?

Quiet check-in (only after a real gap):

> You've been quiet. Everything going well, or are you stuck somewhere?

## Consent (customer-facing copy)

One-time ask, plain words, right after the free three ideas are delivered and
before any paid offer. The incentive is honest: their answers shape the
product they use, which serves their goal of making their first $1.

> One more thing. I'd like to learn what's working for you, so Diamond Hands
> Dig can make this better for you. He reads every word himself, and your
> answers shape what the team does next for you. Nothing with your name,
> employer, or payment details leaves your machine. Say "stop feedback" any
> time and I'll drop it. OK?

- Yes: feedback consent on, for life of the account unless revoked.
- No: consent off. Never ask again, never mention it.
- "stop feedback" at any time: stop asking, delete local cards, send nothing.
- Consent to feedback is not consent to publish. Publishing needs the
  separate story consent flow (first-dollar-stories), always.

## Acknowledgment (customer-facing copy)

After any feedback, before the card is sent:

> Got it. Straight to Diamond Hands. He reads every one of these, and what
> you say decides what we improve for you next.

When a shipped change came from feedback:

> You asked for X. It's live now — that one's from you.

Never promise a change you can't deliver. If you don't know, say so.

## Card format (internal)

One card per moment, sanitized before anything leaves the machine:

```
FEEDBACK CARD
Customer: C-<short code derived from installation id>
Date: YYYY-MM-DD (UTC)
Moment: first-customer | win | friction | confusion | want | busywork | support | quiet
Context: one line, no identifiers
Their words: one line, verbatim
Ask: what they want, if any
Flags: owner-reply | founder-connect | story-candidate | none
```

Never include: name, employer, location, email, payment details, balance,
job counts, or anything that identifies the customer. Customer-visible data
stays on their machine; only the card leaves.

## Delivery

- Primary: the in-session agent sends the card by email to
  hello@hermesstartup.com, subject `Feedback: <moment> C-<code>`.
  Extremes get a `FOUNDER:` prefix in the subject (first customer, refund talk).
- If email is not configured for the customer, keep the card local. When the
  customer next talks to support, the Support bot relays the card.
- The weekly War Room digest compiles all cards.

## The one-on-one

After notable feedback, or once per paid customer, offer the direct line
(Support bot or in-session agent):

> Diamond Hands Dig would like to hear from you directly on Telegram. He
> reads everything himself and wants to know what's working for you, so your
> next steps get sharper. Only he sees your handle. Want me to connect you?

If yes: include the contact in the card with flag `founder-connect`. Diamond
Hands DMs, asks two questions (what's working, what's in the way), and logs
what he learns through his own agent.

## Hard rules

- Every word Hermes Startup sends a customer passes the anti-slop rubric:
  no hype words, no guarantees, plain short sentences, no em dashes, no
  exclamation marks, no emoji.
- Never log or send identifiers. Cards are anonymous by default.
- Never ask for feedback in exchange for anything (no bribe, no discount).
- Never publish any feedback without the separate story consent flow.
- Refund talk or strong friction: flag `owner-reply` and alert Diamond Hands
  the same day, never auto-refund.
