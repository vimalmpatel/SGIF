"""Validate a local SGIF site asset inventory."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("asset_id", "name", "asset_type", "zone", "criticality", "owner")
ALLOWED_CRITICALITIES = {"low", "moderate", "high", "critical"}


def validate_inventory(data: Any) -> list[str]:
    """Return validation errors for an inventory decoded from JSON."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["top level must be a JSON object"]

    assets = data.get("assets")
    if not isinstance(assets, list):
        return ["'assets' must be an array"]

    seen_ids: set[str] = set()
    for index, asset in enumerate(assets):
        location = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{location} must be an object")
            continue

        for field in REQUIRED_FIELDS:
            value = asset.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{location}.{field} must be a non-empty string")

        asset_id = asset.get("asset_id")
        if isinstance(asset_id, str) and asset_id.strip():
            if asset_id in seen_ids:
                errors.append(f"{location}.asset_id duplicates '{asset_id}'")
            seen_ids.add(asset_id)

        criticality = asset.get("criticality")
        if isinstance(criticality, str) and criticality not in ALLOWED_CRITICALITIES:
            allowed = ", ".join(sorted(ALLOWED_CRITICALITIES))
            errors.append(f"{location}.criticality must be one of: {allowed}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a local SGIF asset inventory")
    parser.add_argument("inventory", type=Path, help="path to a JSON inventory file")
    args = parser.parse_args()

    try:
        with args.inventory.open(encoding="utf-8") as inventory_file:
            data = json.load(inventory_file)
    except OSError as error:
        print(f"Cannot read inventory: {error}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as error:
        print(f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}", file=sys.stderr)
        return 1

    errors = validate_inventory(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Valid inventory: {len(data['assets'])} asset(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())