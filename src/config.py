"""Vendor-neutral configuration. Switching model/backend is a string change here only."""

import os


def _load_dotenv() -> None:
    """Reads a .env file at the repo root into os.environ, if present. Minimal by
    design (stdlib only, no new dependency) - existing environment variables always win,
    and a missing .env is not an error (BACKEND="scripted" needs no key at all)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

# "scripted" (default, no network/key) or "live" (real OpenRouter call).
BACKEND = os.environ.get("A2_BACKEND", "scripted")

# Free-tier model while D1/D2 are being built and debugged, so no live testing spends
# real key balance. Swap to a priced model only for the D5(b) battery.
MODEL = os.environ.get("A2_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

BASE_URL = "https://openrouter.ai/api/v1"

# USD per 1M tokens, (input, output). "0/model:free" entries are free-tier and cost $0.
# Extend this table as models are added for the D5(b) live battery.
PRICE_PER_MILLION = {
    "nvidia/nemotron-3-super-120b-a12b:free": (0.0, 0.0),
}


def price_for(model: str) -> tuple[float, float]:
    """Per-token USD prices. Reject unlisted models rather than silently billing zero."""
    if model not in PRICE_PER_MILLION:
        raise ValueError(f"No configured token price for {model!r}; register a price before running")
    per_million_in, per_million_out = PRICE_PER_MILLION[model]
    return per_million_in / 1_000_000, per_million_out / 1_000_000


# Per-run limits. The loop checks exhaustion before the next request and overspend
# before executing tools. A sent live request can still exceed its remaining budget.
BUDGET_CEILING_USD = 1.00
STEP_CAP = 10
# D3 autonomy setting for the irreversible decision-write action.
AUTONOMY = "confirm"
