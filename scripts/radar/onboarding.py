"""Local-only resumable onboarding and deterministic paid-offer qualification."""
from __future__ import annotations

import fcntl
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1"
MAX_ANSWER_CHARS = 2_000
QUESTIONS = (
    {"id": "outcome_urgency", "prompt": "What outcome do you want most right now, and why now rather than later? Be specific about what would actually change for you."},
    {"id": "first_proof", "prompt": "What specific, small result would make you believe this is worth pursuing? What would it look like, and how would you know it happened?"},
    {"id": "constraints", "prompt": "What real time, cash, and risk constraints apply to you this month? What would your honest weekly availability and budget look like?"},
    {"id": "assets", "prompt": "What proven skills, real access, or assets could you actually use today — things you are genuinely good at or already have?"},
    {"id": "past_attempts", "prompt": "What have you already tried toward this, what actually happened, and why did it stop? What was the hardest part?"},
    {"id": "boundaries", "prompt": "What legal, ethical, employer, privacy, or identity boundaries must any path respect? What are you not willing to do?"},
    {"id": "reachable_buyers", "prompt": "Who could you realistically help or learn from first, without using private or employer data? Name the real people or groups you can already reach."},
    {"id": "work_preferences", "prompt": "What kind of work are you genuinely willing to do day to day, and what do you want to avoid? What would you end up loving rather than forcing?"},
    {"id": "market_tolerance", "prompt": "Are you willing to face real market response — including rejection and silence — to learn what actually works? How will you handle it?"},
    {"id": "accountability", "prompt": "How will you stay accountable for one small approved next step? What makes you follow through rather than drift?"},
)
QUESTION_IDS = tuple(question["id"] for question in QUESTIONS)


def _reject_symlinked_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        if current.is_symlink():
            raise ValueError("onboarding state path contains a symlink")


@contextmanager
def _state_lock(path: Path):
    _reject_symlinked_components(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = path.with_name(path.name + ".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _approved_answers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("onboarding answers must be an object")
    answers: dict[str, str] = {}
    for key, answer in value.items():
        if key not in QUESTION_IDS or not isinstance(answer, str):
            raise ValueError("onboarding state contains an unsupported answer")
        if not answer or answer.strip() != answer or len(answer) > MAX_ANSWER_CHARS:
            raise ValueError("onboarding answer is empty or exceeds its limit")
        answers[key] = answer
    return answers


def _read_state(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        raise ValueError("onboarding state path contains a symlink")
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > 32_768 or stat.S_IMODE(info.st_mode) & 0o022:
        raise ValueError("onboarding state file is not trusted")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("onboarding state is unreadable") from None
    if not isinstance(value, dict) or set(value) != {"schema_version", "status", "answers"}:
        raise ValueError("onboarding state schema is invalid")
    if value.get("schema_version") == "1.0" and isinstance(value.get("answers"), dict):
        answers = dict(value["answers"])
        if "evidence_30_days" in answers:
            answers["first_proof"] = answers.pop("evidence_30_days")
        if "commitment" in answers:
            answers["accountability"] = answers.pop("commitment")
        value = {"schema_version": SCHEMA_VERSION, "status": value["status"], "answers": answers}
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("onboarding state schema is unsupported")
    answers = _approved_answers(value.get("answers"))
    expected_status = "completed" if len(answers) == len(QUESTION_IDS) else "in_progress"
    if value.get("status") != expected_status:
        raise ValueError("onboarding state status is inconsistent")
    return {"schema_version": SCHEMA_VERSION, "status": expected_status, "answers": answers}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            os.fchmod(temporary.fileno(), 0o600)
            json.dump(state, temporary, sort_keys=True, separators=(",", ":"))
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _present(state: dict[str, Any]) -> dict[str, Any]:
    result = {
        "schema_version": state["schema_version"],
        "status": state["status"],
        "answers": dict(state["answers"]),
        "privacy": {"local_only": True, "raw_content_uploaded": False},
    }
    for number, question in enumerate(QUESTIONS, start=1):
        if question["id"] not in state["answers"]:
            result["next_question"] = {**question, "number": number, "total": len(QUESTIONS)}
            break
    else:
        result["next_question"] = None
    return result


def start_onboarding(state_path: str | Path) -> dict[str, Any]:
    path = Path(state_path)
    with _state_lock(path):
        state = _read_state(path)
        if state is None:
            state = {"schema_version": SCHEMA_VERSION, "status": "in_progress", "answers": {}}
            _write_state(path, state)
        return _present(state)


def load_onboarding(state_path: str | Path) -> dict[str, Any] | None:
    path = Path(state_path)
    with _state_lock(path):
        state = _read_state(path)
        return _present(state) if state is not None else None


def answer_onboarding(state_path: str | Path, question_id: str, answer: str) -> dict[str, Any]:
    if question_id not in QUESTION_IDS:
        raise ValueError("unknown onboarding question")
    approved = _approved_answers({question_id: answer})[question_id]
    path = Path(state_path)
    with _state_lock(path):
        state = _read_state(path)
        if state is None:
            raise ValueError("onboarding has not been started")
        answers = dict(state["answers"])
        answers[question_id] = approved
        status = "completed" if len(answers) == len(QUESTION_IDS) else "in_progress"
        state = {"schema_version": SCHEMA_VERSION, "status": status, "answers": answers}
        _write_state(path, state)
        return _present(state)


def qualify_onboarding(state_path: str | Path) -> dict[str, Any]:
    loaded = load_onboarding(state_path)
    if loaded is None:
        raise ValueError("onboarding has not been started")
    missing = [question_id for question_id in QUESTION_IDS if question_id not in loaded["answers"]]
    if missing:
        return {"schema_version": SCHEMA_VERSION, "qualification": "incomplete", "paid_offer_allowed": False, "missing_questions": missing, "gaps": ["Complete or explicitly skip each remaining onboarding question."]}
    answers = loaded["answers"]
    gaps = []
    if answers["market_tolerance"].strip().lower() not in {"willing", "yes", "ready"}:
        gaps.append("Choose one ethical way to face real market response and rejection.")
    if answers["accountability"].strip().lower() not in {"committed", "yes", "ready"}:
        gaps.append("Choose one way to stay accountable for a reversible next action.")
    if answers["assets"].strip().lower() in {"prefer_not_to_say", "provided", "none", "n/a", "na", "not sure", "unknown"}:
        gaps.append("Provide enough truthful context for at least one plausible hypothesis.")
    return {"schema_version": SCHEMA_VERSION, "qualification": "not_yet" if gaps else "qualified", "paid_offer_allowed": not gaps, "missing_questions": [], "gaps": gaps}


def delete_onboarding(state_path: str | Path) -> bool:
    path = Path(state_path)
    with _state_lock(path):
        if not _onboarding_deletable_unlocked(path):
            return False
        path.unlink()
        return True


def validate_onboarding_deletable(state_path: str | Path) -> bool:
    path = Path(state_path)
    with _state_lock(path):
        return _onboarding_deletable_unlocked(path)


def _onboarding_deletable_unlocked(path: Path) -> bool:
    if path.is_symlink():
        raise ValueError("onboarding state path contains a symlink")
    try:
        info = path.stat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("onboarding state file is not trusted")
    return True
