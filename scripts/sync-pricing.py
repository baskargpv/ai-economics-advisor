"""Diff data/pricing.json against LiteLLM's model_prices_and_context_window.json.

Dry-run by default: fetches LiteLLM's catalogue and prints a per-model diff
against our curated pricing table. Nothing is written unless --write is
passed, and even then only the numeric fields below are touched — tier,
notes, promotional flags, and displayName stay under manual review, since
those carry judgment calls a diff can't make safely.

Usage:
    python scripts/sync-pricing.py            # dry run, prints diff
    python scripts/sync-pricing.py --write     # applies changes to pricing.json

LiteLLM's file (MIT licensed): https://github.com/BerriAI/litellm
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import requests

LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
PRICING_PATH = Path(__file__).parent.parent / "data" / "pricing.json"

# Our model id -> LiteLLM catalogue key. Most are 1:1; a few need an
# explicit pick where LiteLLM tracks near-identical variants (e.g. two
# Gemini point releases with the same price) or provider-prefixed keys.
MODEL_ID_MAP = {
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-sonnet-5": "claude-sonnet-5",
    "claude-opus-5": "claude-opus-5",
    "claude-fable-5": "claude-fable-5",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gemini-3-flash-lite": "gemini-3.1-flash-lite",
    "gemini-3-flash": "gemini-3.7-flash",
    "gemini-3-1-pro": "gemini-3.1-pro-preview",
}

TOLERANCE_PCT = 0.5  # below this, treat as no meaningful change


def fetch_litellm_catalogue():
    resp = requests.get(LITELLM_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def per_million(litellm_entry, field):
    value = litellm_entry.get(field)
    return round(value * 1_000_000, 4) if value is not None else None


def pct_change(old, new):
    if old in (None, 0):
        return None
    return (new - old) / old * 100


def diff_model(our_model, litellm_entry):
    """Return list of (field, old, new, pct) for fields that differ beyond tolerance."""
    changes = []
    field_map = {
        "inputCostPerMillion": "input_cost_per_token",
        "outputCostPerMillion": "output_cost_per_token",
        "cachedInputCostPerMillion": "cache_read_input_token_cost",
    }
    for our_field, litellm_field in field_map.items():
        new_value = per_million(litellm_entry, litellm_field)
        old_value = our_model.get(our_field)
        if new_value is None:
            continue
        change = pct_change(old_value, new_value)
        if change is None or abs(change) >= TOLERANCE_PCT:
            changes.append((our_field, old_value, new_value, change))

    new_context = litellm_entry.get("max_input_tokens")
    old_context = our_model.get("contextWindow")
    if new_context is not None and new_context != old_context:
        changes.append(("contextWindow", old_context, new_context, None))

    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Apply changes to data/pricing.json"
    )
    args = parser.parse_args()

    with open(PRICING_PATH) as f:
        pricing_data = json.load(f)

    print(f"Fetching {LITELLM_URL} ...")
    catalogue = fetch_litellm_catalogue()

    any_changes = False
    any_unmatched = False

    for model in pricing_data["models"]:
        model_id = model["id"]
        litellm_key = MODEL_ID_MAP.get(model_id)
        if litellm_key is None:
            print(f"[SKIP] {model_id}: no LiteLLM mapping in MODEL_ID_MAP")
            any_unmatched = True
            continue
        if litellm_key not in catalogue:
            print(f"[NOT FOUND] {model_id}: '{litellm_key}' missing from LiteLLM catalogue")
            any_unmatched = True
            continue

        entry = catalogue[litellm_key]
        changes = diff_model(model, entry)
        if not changes:
            print(f"[OK] {model_id}: matches LiteLLM within {TOLERANCE_PCT}%")
            continue

        any_changes = True
        print(f"[CHANGED] {model_id} (litellm key: {litellm_key})")
        for field, old, new, pct in changes:
            pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
            print(f"    {field}: {old} -> {new}{pct_str}")

        if args.write:
            for field, _old, new, _pct in changes:
                model[field] = new

    if any_unmatched:
        print(
            "\nSome models were skipped or not found — add/fix their entry in "
            "MODEL_ID_MAP before trusting this sync as complete."
        )

    if args.write and any_changes:
        pricing_data["lastUpdated"] = date.today().isoformat()
        with open(PRICING_PATH, "w") as f:
            json.dump(pricing_data, f, indent=2)
            f.write("\n")
        print(f"\nWrote updated prices to {PRICING_PATH}")
        print("Review the diff above, update any affected 'notes'/'promotional' fields by hand, and run pytest before committing.")
    elif not args.write and any_changes:
        print("\nDry run only — rerun with --write to apply these changes.")
    elif not any_changes:
        print("\nNo pricing changes detected.")

    return 1 if any_unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
