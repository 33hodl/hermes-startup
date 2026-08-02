"""Premium shareable flex-card renderer (deterministic 1200x630 SVG).

Market Hermes Startup itself (hermesstartup.com), not the underlying platform.
Every card is a factual, outcome-first statement with a clear viewer CTA so
someone seeing the card knows exactly how to do the same. Generated locally and
deterministically: zero server cost, identical quality for every user. Income is
only ever referenced on the ``first_dollar`` milestone (the user's own achieved
outcome) and never promised.
"""
from __future__ import annotations

import html
from typing import Literal

Milestone = Literal["questions_complete", "build_started", "business_launched", "first_dollar"]

_HEADLINES: dict[Milestone, tuple[str, str, str]] = {
    # (headline, sub, cta) — headlines are kept to ONE line at the display size.
    "questions_complete": (
        "Three ideas built just for me.",
        "Picked from ten private answers.",
        "Answer 10 questions and start free at hermesstartup.com",
    ),
    "build_started": (
        "My business is being built now.",
        "Step by step with Hermes Startup.",
        "Make your first $1 at hermesstartup.com",
    ),
    "business_launched": (
        "My business just went live.",
        "Built with Hermes Startup.",
        "Start yours at hermesstartup.com",
    ),
    "first_dollar": (
        "I just made my first $1.",
        "Outcome earned on my own terms, with Hermes Startup.",
        "You can too. Start free at hermesstartup.com",
    ),
}

_GOLD = "#d8b45e"
_GOLD_DIM = "#b89a48"
_INK = "#10141b"
_TEXT = "#f3efe6"
_MUTED = "#a8a896"
_PANEL = "#161b24"
_RULE = "#2c3340"


def _measure(text: str, size: int, factor: float = 0.60) -> float:
    """Estimated rendered width of ``text`` in Georgia serif at ``size`` px."""
    return len(text) * factor * size


def _fit_lines(text: str, size: int, width: int = 1000) -> list[str]:
    """Greedy word-wrap so every line fits inside ``width`` (never clips)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _measure(candidate, size) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def render_flex_card(
    milestone: Milestone,
    *,
    goal: str | None = None,
    fact: str | None = None,
    custom: str | None = None,
    version: str = "0.1.2",
) -> str:
    if milestone not in _HEADLINES:
        raise ValueError("unknown milestone")
    headline, sub, cta = _HEADLINES[milestone]
    fact_text = html.escape(str(fact or ""))[:120]
    custom_text = html.escape(str(custom or ""))[:90]
    goal_text = html.escape(str(goal or "my chosen business"))[:80]
    escape = html.escape

    # Fixed vertical bands so nothing can collide. Headlines are one line.
    headline_size = 50
    headline_lines = _fit_lines(headline, headline_size)
    line_h = 56
    headline_top = 240
    last_line_baseline = headline_top + (len(headline_lines) - 1) * line_h + 42
    headline_el = "".join(
        f'<text x="72" y="{headline_top + i * line_h + 42}" font-family="Georgia, serif" font-size="{headline_size}" '
        f'font-weight="600" fill="{_TEXT}" letter-spacing="-0.5">{escape(text)}</text>'
        for i, text in enumerate(headline_lines)
    )
    sub_base = last_line_baseline + 40
    custom_base = sub_base + 42 if custom_text else None
    label_base = (custom_base if custom_text else sub_base) + 82
    fact_base = label_base + 34

    custom_el = ""
    if custom_text:
        custom_el = (
            f'<text x="72" y="{custom_base}" font-family="Georgia, serif" font-size="24" font-style="italic" '
            f'fill="{_MUTED}">{custom_text}</text>'
        )

    outcome_el = ""
    if fact_text:
        outcome_el = (
            f'<text x="72" y="{label_base}" font-family="Arial, Helvetica, sans-serif" font-size="19" '
            f'font-weight="600" letter-spacing="3" fill="{_GOLD}">OUTCOME</text>'
            f'<text x="72" y="{fact_base}" font-family="Georgia, serif" font-size="30" fill="{_TEXT}">{fact_text}</text>'
        )

    # CTA pill is a full-width bottom band; footer line sits under it.
    pill_top = 508
    pill_text = cta
    pill_w = max(_measure(pill_text, 25, 0.62) + 112, 660)
    pill_x = (1200 - pill_w) / 2

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="Hermes Startup {escape(milestone)} share card">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="#141a23"/><stop offset="1" stop-color="#0b0e14"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0" r="1" gradientUnits="objectBoundingBox">
      <stop offset="0" stop-color="#2a3140" stop-opacity="0.55"/><stop offset="1" stop-color="#0b0e14" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect x="0" y="0" width="1200" height="6" fill="{_GOLD}"/>
  <g>
    <rect x="72" y="64" width="48" height="48" rx="12" fill="{_GOLD}"/>
    <text x="96" y="100" font-family="Georgia, serif" font-size="30" font-weight="700" fill="{_INK}" text-anchor="middle">H</text>
    <text x="136" y="97" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="{_TEXT}" letter-spacing="-0.6">hermesstartup.com</text>
    <text x="1128" y="97" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="{_MUTED}" text-anchor="end">v{escape(version)}</text>
  </g>
  {headline_el}
  <text x="72" y="{sub_base}" font-family="Georgia, serif" font-size="26" font-style="italic" fill="{_GOLD}">{escape(sub)}</text>
  {custom_el}
  {outcome_el}
  <rect x="{pill_x}" y="{pill_top}" width="{pill_w}" height="56" rx="28" fill="{_PANEL}" stroke="{_GOLD}" stroke-width="1.5"/>
  <text x="{pill_x + pill_w / 2}" y="{pill_top + 36}" font-family="Arial, Helvetica, sans-serif" font-size="25" font-weight="700" fill="{_TEXT}" text-anchor="middle">{escape(pill_text)}</text>
  <g>
    <line x1="72" y1="592" x2="1128" y2="592" stroke="{_RULE}" stroke-width="1"/>
    <text x="72" y="616" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="{_MUTED}">Your first $1, guided step by step.</text>
  </g>
</svg>
"""
