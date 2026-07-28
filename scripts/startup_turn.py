#!/usr/bin/env python3
"""Execute one local Hermes Startup turn from a bounded JSON stdin request."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent
if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

from radar.startup import startup_turn

MAX_REQUEST_BYTES = 16_384


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute one local Hermes Startup turn from JSON stdin.")
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        print(json.dumps({"schema_version": "1.0", "status": "request_rejected", "reason": "invalid_or_oversized_request"}, sort_keys=True))
        return 2
    try:
        request = json.loads(raw)
        result = startup_turn(args.state_dir, request)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        print(json.dumps({"schema_version": "1.0", "status": "request_rejected", "reason": "invalid_request"}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({"schema_version": "1.0", "status": "error", "reason": "local_startup_unavailable"}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
