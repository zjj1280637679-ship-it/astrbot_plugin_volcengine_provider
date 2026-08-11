"""Dry-run planner for the provider-card E2E matrix.

This stage is intentionally dependency-free. It validates the declarative
matrix before browser/API execution is added, so later failures can be located
in UI/runtime layers rather than confused with a malformed test inventory.
"""

from __future__ import annotations

import json
from pathlib import Path

from assertions import (
    assert_matrix_provider_entry,
    assert_unique_provider_ids,
)

HERE = Path(__file__).resolve().parent
MATRIX_PATH = HERE / "matrix.json"


def load_matrix() -> dict:
    data = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise AssertionError(f"unsupported matrix schema_version: {data.get('schema_version')!r}")

    providers = data.get("providers")
    if not isinstance(providers, list) or not providers:
        raise AssertionError("matrix.providers must be a non-empty list")

    assert_unique_provider_ids(providers)
    for entry in providers:
        if not isinstance(entry, dict):
            raise AssertionError("each provider matrix entry must be an object")
        assert_matrix_provider_entry(entry)

    invariants = data.get("global_invariants")
    if not isinstance(invariants, list) or not invariants:
        raise AssertionError("matrix.global_invariants must be a non-empty list")
    return data


def build_plan(matrix: dict) -> list[dict]:
    plan: list[dict] = []
    for provider in matrix["providers"]:
        for path in provider["card_paths"]:
            plan.append(
                {
                    "layer": "card_ui_lifecycle",
                    "provider_id": provider["id"],
                    "source_type": provider["source_type"],
                    "scenario": path,
                }
            )
        for scenario in provider["runtime"]:
            plan.append(
                {
                    "layer": "runtime",
                    "provider_id": provider["id"],
                    "source_type": provider["source_type"],
                    "scenario": scenario,
                }
            )
        for migration in provider.get("migration_cases", []):
            plan.append(
                {
                    "layer": "migration",
                    "provider_id": provider["id"],
                    "source_type": provider["source_type"],
                    "scenario": migration,
                }
            )
    return plan


def main() -> None:
    matrix = load_matrix()
    plan = build_plan(matrix)
    summary = {
        "providers": len(matrix["providers"]),
        "planned_scenarios": len(plan),
        "global_invariants": len(matrix["global_invariants"]),
        "layers": sorted({item["layer"] for item in plan}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
