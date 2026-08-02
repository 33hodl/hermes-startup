"""Official-document capability catalog used before Hermes Startup plans execution."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


OFFICIAL_HERMES_LLM_INDEX_URL = "https://hermes-agent.nousresearch.com/docs/llms.txt"
_MAX_PUBLIC_RESPONSE_BYTES = 1_000_000
_ENTRY = re.compile(r"^- \[([^\]]+)\]\((https://hermes-agent\.nousresearch\.com/docs/[^)]+)\)(?::\s*(.*))?$")
_HEADING = re.compile(r"^##\s+(.+?)\s*$")


def _fetch_public_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "hermes-startup-capability-review/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read(_MAX_PUBLIC_RESPONSE_BYTES + 1)
    if len(body) > _MAX_PUBLIC_RESPONSE_BYTES:
        raise ValueError("official capability catalog response too large")
    return body.decode("utf-8")


def _identifier(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _parse_catalog(document: str) -> list[dict[str, str]]:
    category = "Other"
    entries: list[dict[str, str]] = []
    for raw_line in document.splitlines():
        line = raw_line.strip().replace("\\-", "-").replace("\\[", "[").replace("\\]", "]")
        heading = _HEADING.match(line.replace("\\#", "#"))
        if heading:
            category = heading.group(1)
            continue
        match = _ENTRY.match(line)
        if not match:
            continue
        title, url, description = match.groups()
        parsed = urlparse(url)
        if parsed.hostname != "hermes-agent.nousresearch.com" or not parsed.path.startswith("/docs/"):
            continue
        entries.append(
            {
                "id": _identifier(title),
                "title": title,
                "category": category,
                "url": url,
                "description": (description or "").strip(),
                "availability": "documented_publicly_not_locally_verified",
            }
        )
    unique = {entry["id"]: entry for entry in entries}
    result = sorted(unique.values(), key=lambda entry: entry["id"])
    if len(result) < 3 or not any(entry["id"] == "cron-jobs" for entry in result):
        raise ValueError("official capability catalog could not be verified")
    return result


def _save(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            os.fchmod(temporary.fileno(), 0o600)
            json.dump(result, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class OfficialHermesCatalog:
    """Refresh a small, auditable catalog from the official generated docs index."""

    def __init__(self, fetch_text: Callable[[str], str] = _fetch_public_text):
        self._fetch_text = fetch_text

    def refresh(self, state_path: Path, *, retrieved_at: str) -> dict[str, object]:
        document = self._fetch_text(OFFICIAL_HERMES_LLM_INDEX_URL)
        capabilities = _parse_catalog(document)
        result: dict[str, object] = {
            "schema_version": "0.1",
            "status": "refreshed",
            "source": {
                "kind": "official",
                "url": OFFICIAL_HERMES_LLM_INDEX_URL,
                "retrieved_at": retrieved_at,
                "content_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
            "capabilities": capabilities,
            "next_step": "Verify the needed capability is installed, enabled, and appropriate before using it in an idea or action plan.",
            "privacy": {"public_query_contains_setup_data": False, "raw_user_data_stored": False},
        }
        _save(state_path, {key: result[key] for key in ("schema_version", "source", "capabilities")})
        return result
