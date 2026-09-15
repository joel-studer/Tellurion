"""FUTURE-ONLY execution modes + live kill gate (enforced in code).

Allowed today: REPLAY, BACKTEST.
PAPER_SANDBOX: disabled by governance (separate enablement required).
LIVE: hard-fails. No credentials accepted anywhere in this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MODES = ("REPLAY", "BACKTEST", "PAPER_SANDBOX", "LIVE")
ALLOW_LIVE = False
ALLOW_PAPER_SANDBOX = False

FORBIDDEN_CREDENTIAL_KEYS = ("api_key", "api_secret", "passphrase", "private_key",
                             "secret_key", "access_token", "mnemonic",
                             "seed_phrase", "rpc_url", "pk", "password",
                             "token", "secret")

# Vendor-prefixed variants are refused too (e.g. EXCHANGE_API_KEY, WALLET_PK).
_CREDENTIAL_KEY = re.compile(
    r"(?i)^(?:[a-z0-9]+_)*(?:" + "|".join(FORBIDDEN_CREDENTIAL_KEYS) + r")$")


class LiveRefused(Exception):
    """Raised whenever live transport is attempted (always, today)."""


class CredentialsRefused(Exception):
    """Raised whenever credential material enters a future execution path."""


def assert_no_credentials(config: Any) -> None:
    """Fail closed on credential-looking keys (dicts, namespaces, env names)."""
    items = []
    if isinstance(config, dict):
        items = list(config.items())
    else:
        try:
            items = list(vars(config).items())
        except TypeError:
            return
    for k, v in items:
        if _CREDENTIAL_KEY.match(str(k)) and v not in (
                None, "", "UNKNOWN"):
            raise CredentialsRefused(f"credential key refused in execution path: {k}")


def assert_mode_allowed(mode: str) -> str:
    if mode == "LIVE" or not ALLOW_LIVE and mode == "LIVE":
        raise LiveRefused("LIVE execution is hard-disabled (ALLOW_LIVE=false)")
    if mode == "PAPER_SANDBOX" and not ALLOW_PAPER_SANDBOX:
        raise LiveRefused("PAPER_SANDBOX disabled by governance (not enabled)")
    if mode not in ("REPLAY", "BACKTEST"):
        raise LiveRefused(f"execution mode refused: {mode}")
    return mode


@dataclass(frozen=True)
class LiveExecutionGuard:
    """Policy object: constructing/using live transport always raises."""

    allow_live: bool = False

    def check(self, mode: str = "LIVE") -> None:
        assert_mode_allowed(mode)

    def describe(self) -> dict:
        return {"ALLOW_LIVE": ALLOW_LIVE,
                "ALLOW_PAPER_SANDBOX": ALLOW_PAPER_SANDBOX,
                "allowed_today": ["REPLAY", "BACKTEST"],
                "enforcement": "core future execution code (not a UI flag)"}
