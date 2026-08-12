#!/usr/bin/env python3
"""Fail release preparation when documentation authority drifts.

This intentionally checks only HOT-authority consistency. Historical documents
may contain older versions and completed goals without failing this guard.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_json(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        fail(f"required knowledge-state file missing: {relative}")
    try:
        value = json.loads(path.read_text("utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {relative}: {exc}")
    if not isinstance(value, dict):
        fail(f"{relative} must contain a JSON object")
    return value


def metadata_version() -> str:
    text = (ROOT / "metadata.yaml").read_text("utf-8")
    match = re.search(r'(?m)^\s*version\s*:\s*["\']?([^"\'\r\n#]+)', text)
    if not match:
        fail("metadata.yaml has no readable version")
    return match.group(1).strip()


def require_hot_pointer(relative: str) -> None:
    text = (ROOT / relative).read_text("utf-8")
    if "docs/PROJECT_STATE.json" not in text:
        fail(f"{relative} must point readers to docs/PROJECT_STATE.json as HOT state")


def main() -> int:
    version = metadata_version()
    state = read_json("docs/PROJECT_STATE.json")
    decisions = read_json("docs/DECISION_INDEX.json")

    if state.get("role") != "hot_state_authority":
        fail("PROJECT_STATE role must be hot_state_authority")

    development = state.get("development")
    if not isinstance(development, dict):
        fail("PROJECT_STATE.development must be an object")
    if str(development.get("version")) != version:
        fail(
            "metadata/PROJECT_STATE version drift: "
            f"metadata={version!r} development={development.get('version')!r}"
        )

    frontier = state.get("active_validation_frontier")
    if not isinstance(frontier, dict):
        fail("PROJECT_STATE.active_validation_frontier must be an object")
    if str(frontier.get("release")) != version:
        fail(
            "active validation frontier belongs to a different release: "
            f"metadata={version!r} frontier={frontier.get('release')!r}"
        )

    goal = state.get("current_goal")
    if not isinstance(goal, dict) or not str(goal.get("id") or "").strip():
        fail("PROJECT_STATE.current_goal must contain a non-empty id")

    lifecycle = state.get("knowledge_lifecycle")
    if not isinstance(lifecycle, dict):
        fail("PROJECT_STATE.knowledge_lifecycle must be an object")
    if lifecycle.get("hot_authority") != "docs/PROJECT_STATE.json":
        fail("PROJECT_STATE knowledge lifecycle must self-identify as HOT authority")
    if lifecycle.get("cold_archive") != "docs/archive/":
        fail("PROJECT_STATE must identify docs/archive/ as the cold archive")

    if decisions.get("role") != "warm_navigation_only":
        fail("DECISION_INDEX must be warm_navigation_only")
    if decisions.get("hot_state") != "docs/PROJECT_STATE.json":
        fail("DECISION_INDEX must point to PROJECT_STATE instead of copying HOT state")

    forbidden_decision_keys = {
        "release",
        "active_evidence",
        "active_validation_frontier",
        "current_goal",
        "current_strategy",
    }
    leaked = sorted(forbidden_decision_keys.intersection(decisions))
    if leaked:
        fail(f"DECISION_INDEX duplicated HOT authority keys: {leaked}")

    for relative in (
        "AGENTS.md",
        "docs/AI_RULES.md",
        "docs/AI_ONBOARDING.md",
        "docs/DESIGN_DECISIONS.md",
        "docs/E2E_MATRIX.md",
    ):
        require_hot_pointer(relative)

    if not (ROOT / "docs/archive/README.md").is_file():
        fail("docs/archive/README.md is required for explicit cold-zone semantics")
    if not (ROOT / "docs/archive/PROJECT_STATE-0.1.18.md").is_file():
        fail("0.1.18 completed HOT frontier must remain demoted in docs/archive")

    old_graph = read_json("strategy/executable-model-graph-v0.1.json")
    new_graph = read_json("strategy/executable-model-graph-v0.2.json")
    old_lifecycle = old_graph.get("lifecycle")
    new_lifecycle = new_graph.get("lifecycle")
    if not isinstance(old_lifecycle, dict) or old_lifecycle.get("status") != "superseded":
        fail("strategy v0.1 must be explicitly superseded")
    if old_lifecycle.get("superseded_by") != "strategy/executable-model-graph-v0.2.json":
        fail("strategy v0.1 must identify v0.2 as its successor")
    if not isinstance(new_lifecycle, dict) or new_lifecycle.get("status") not in {"warm", "active"}:
        fail("strategy v0.2 must identify an explicit non-superseded lifecycle state")

    print(
        "KNOWLEDGE_STATE_OK "
        f"development={version} hot=docs/PROJECT_STATE.json "
        "decision_index=warm archive=docs/archive/"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"KNOWLEDGE_STATE_ERROR: {exc}", file=sys.stderr)
        raise
