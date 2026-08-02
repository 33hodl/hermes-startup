#!/usr/bin/env python3
"""Refresh a local Hermes Agent capability catalog from official documentation."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from radar.hermes_capabilities import OfficialHermesCatalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the official Hermes Agent capability catalog without sending setup data.")
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = OfficialHermesCatalog().refresh(
            args.state_dir / "hermes-capabilities.json",
            retrieved_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({"schema_version": "0.1", "status": "unavailable", "reason": "official_capability_catalog_unavailable_or_unverified"}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
