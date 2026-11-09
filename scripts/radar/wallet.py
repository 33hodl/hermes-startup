"""Read-only prepaid-wallet client for the Hermes Startup API.

The customer's balance lives on the Hermes Startup API. This module is the ONLY
network path the skill uses for balance checks: it activates the anonymous
installation id (the same non-secret id the purchase flow binds to) and reads
``GET /v1/wallet``. It is strictly read-only — it never writes, never spends,
and never fabricates a balance. Any failure (unreachable, HTTP error, invalid
payload) raises :class:`WalletUnavailable` with a machine-readable reason; the
caller must fail closed.

Activation is rate-limited per client address, so the bearer token is cached
locally (mode 0600) and reused across checks. A rejected token (401) triggers
exactly one re-activation; anything else fails closed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# The same bounded anonymous installation-id shape the API accepts.
_INSTALLATION_ID = re.compile(r"^[0-9a-f]{32}$")
# The public API route is live (2026-08-15); the default points at the public host.
_DEFAULT_API_BASE_URL = "https://api.hermesstartup.com"
_MAX_RESPONSE_BYTES = 64 * 1024
_REQUEST_TIMEOUT_SECONDS = 10
_TOKEN_FILE = "wallet-token"
_PROOF_FILE = "installation_proof.json"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Loopback hosts may be plain http (local test servers only); everything else
# must be https so a wallet read can never leak over a cleartext channel.
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class WalletUnavailable(RuntimeError):
    """The wallet could not be read. Never fabricate a balance."""


class _TokenRejected(WalletUnavailable):
    """The cached bearer token was rejected (401); the caller may re-activate once."""


def _validate_api_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("HERMES_STARTUP_API_BASE_URL must not be empty")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" and parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("API base URL must use https")
    if not parsed.hostname:
        raise ValueError("API base URL must include a host")
    if parsed.query or parsed.fragment:
        raise ValueError("API base URL must not include a query or fragment")
    return base_url.rstrip("/")


def api_base_url() -> str:
    """Resolve the Hermes Startup API base URL (env override or public default)."""
    return _validate_api_base_url(os.environ.get("HERMES_STARTUP_API_BASE_URL", _DEFAULT_API_BASE_URL))


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "hermes-startup-wallet/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise _TokenRejected("wallet_service_authentication_failed") from error
        raise WalletUnavailable("wallet_service_unreachable") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise WalletUnavailable("wallet_service_unreachable") from error
    if len(body) > _MAX_RESPONSE_BYTES:
        raise WalletUnavailable("wallet_service_response_too_large")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WalletUnavailable("wallet_service_invalid_response") from error
    if not isinstance(parsed, dict):
        raise WalletUnavailable("wallet_service_invalid_response")
    return parsed


def _get_json(base_url: str, path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "hermes-startup-wallet/0.1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise _TokenRejected("wallet_service_authentication_failed") from error
        raise WalletUnavailable("wallet_service_unreachable") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise WalletUnavailable("wallet_service_unreachable") from error
    if len(body) > _MAX_RESPONSE_BYTES:
        raise WalletUnavailable("wallet_service_response_too_large")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WalletUnavailable("wallet_service_invalid_response") from error
    if not isinstance(parsed, dict):
        raise WalletUnavailable("wallet_service_invalid_response")
    return parsed


def _installation_proof(state_dir: Path) -> str:
    """Return (creating once if needed) the private activation proof.

    The proof is a 32-byte random value kept in its own 0600 file next to the
    cached token, never inside the non-secret installation id. Activation sends
    only ``HMAC-SHA256(key=proof, msg=installation_id)``, so a leaked
    installation id alone can no longer obtain a server credential.
    """

    path = state_dir / _PROOF_FILE
    if path.is_symlink():
        raise WalletUnavailable("wallet_proof_refused_symlink")
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WalletUnavailable("wallet_proof_read_failed") from error
        proof = value.get("installation_proof") if isinstance(value, dict) else None
        if not isinstance(proof, str) or not _HEX64.fullmatch(proof):
            raise WalletUnavailable("wallet_proof_invalid")
        return proof
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise WalletUnavailable("wallet_proof_write_failed") from error
    proof = secrets.token_hex(32)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f"{_PROOF_FILE}.", dir=str(state_dir))
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"schema_version": 1, "installation_proof": proof}, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise WalletUnavailable("wallet_proof_write_failed") from error
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return proof


def _activate(base_url: str, installation_id: str, state_dir: Path | None = None) -> str:
    if state_dir is not None:
        proof = _installation_proof(state_dir)
    else:
        # No state directory: an ephemeral proof can still enrol a brand-new
        # account, but cannot (and must not) claim an already-bound one.
        proof = secrets.token_hex(32)
    transmitted = hmac.new(proof.encode("utf-8"), installation_id.encode("utf-8"), hashlib.sha256).hexdigest()
    activated = _post_json(
        base_url, "/v1/activate", {"installation_id": installation_id, "proof": transmitted}
    )
    token = activated.get("token")
    if not isinstance(token, str) or not token:
        raise WalletUnavailable("wallet_service_activation_failed")
    return token


def _read_cached_token(state_dir: Path) -> str | None:
    path = state_dir / _TOKEN_FILE
    if not path.exists() or path.is_symlink():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise WalletUnavailable("wallet_token_read_failed") from error
    return value if value else None


def _write_cached_token(state_dir: Path, token: str) -> None:
    """Persist the bearer token atomically, mode 0600, refusing symlinks.

    The token is written to an exclusive temp file (created already 0600 and
    re-tightened before any content lands) in the same directory, then renamed
    into place with :func:`os.replace`. A concurrent reader can never observe a
    partial token, and a pre-planted symlink at the cache path is refused so a
    writable state directory cannot redirect the write elsewhere. Any OS-level
    failure surfaces as :class:`WalletUnavailable` (fail closed) instead of
    being swallowed.
    """
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise WalletUnavailable("wallet_token_write_failed") from error
    path = state_dir / _TOKEN_FILE
    if path.is_symlink():
        raise WalletUnavailable("wallet_token_refused_symlink")
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f"{_TOKEN_FILE}.", dir=str(state_dir))
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(token)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise WalletUnavailable("wallet_token_write_failed") from error
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def fetch_wallet_balance(base_url: str, installation_id: str, state_dir: str | Path | None = None) -> dict[str, Any]:
    """Read the exact prepaid balance for an anonymous installation.

    The bearer token is cached under ``state_dir`` (mode 0600) and reused so
    repeated checks do not burn the API's per-address activation rate
    limit. A rejected token re-activates exactly once. Returns the control
    plane's wallet status verbatim (integer microdollars, currency, low-balance
    notice flag). Raises :class:`WalletUnavailable` with a machine-readable
    reason on any failure — never a partial or made-up number.
    """
    base_url = _validate_api_base_url(base_url)
    if not isinstance(installation_id, str) or not _INSTALLATION_ID.fullmatch(installation_id):
        raise ValueError("installation_id must be 32 lowercase hex characters")

    state_path = Path(state_dir) if state_dir is not None else None
    cached_token = _read_cached_token(state_path) if state_path is not None else None

    if cached_token is not None:
        try:
            return _get_json(base_url, "/v1/wallet", cached_token)
        except _TokenRejected:
            # The cached token is stale; fall through and re-activate once.
            pass

    token = _activate(base_url, installation_id, state_path)
    if state_path is not None:
        _write_cached_token(state_path, token)
    return _get_json(base_url, "/v1/wallet", token)
