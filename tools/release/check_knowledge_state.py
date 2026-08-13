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
    version = match.group(1).strip()
    if re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)",
        version,
    ) is None:
        fail(f"metadata version must be an unsigned three-part release: {version!r}")
    return version


def require_hot_pointer(relative: str) -> None:
    text = (ROOT / relative).read_text("utf-8")
    if "docs/PROJECT_STATE.json" not in text:
        fail(f"{relative} must point readers to docs/PROJECT_STATE.json as HOT state")


def reject_active_release_version_literals() -> None:
    """Keep metadata.yaml as the single release-version source for active CI."""

    active_release_files = (
        "tools/release/build_runtime_package.py",
        ".github/workflows/runtime-distribution-gate.yml",
        ".github/workflows/publish-runtime-branch.yml",
        ".github/workflows/validate-runtime-store-source.yml",
    )
    forbidden_patterns = {
        "EXPECTED_VERSION assignment": re.compile(
            r"(?m)^\s*EXPECTED_VERSION\s*="
        ),
        "literal manifest version comparison": re.compile(
            r"manifest\[['\"]version['\"]\]\s*(?:==|!=)\s*['\"]\d+\.\d+\.\d+"
        ),
        "literal metadata version comparison": re.compile(
            r"metadata\[['\"]version['\"]\]\s*(?:==|!=)\s*['\"]\d+\.\d+\.\d+"
        ),
        "literal runtime candidate version": re.compile(
            r"runtime candidate:\s*\d+\.\d+\.\d+"
        ),
    }

    for relative in active_release_files:
        text = (ROOT / relative).read_text("utf-8")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(text):
                fail(f"{relative} contains {label}; derive it from metadata.yaml")


def require_pinned_external_actions() -> None:
    """Prevent floating action tags from changing trusted CI code."""

    uses_pattern = re.compile(r"(?m)^\s*(?:-\s*)?uses\s*:\s*([^\s#]+)")
    commit_pattern = re.compile(r"[0-9a-f]{40}")
    workflow_root = ROOT / ".github/workflows"
    workflows = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflow_root.glob(pattern)
    )
    for workflow in workflows:
        for action in uses_pattern.findall(workflow.read_text("utf-8")):
            if action.startswith("./"):
                continue
            _, separator, ref = action.rpartition("@")
            if not separator or commit_pattern.fullmatch(ref) is None:
                fail(
                    f"{workflow.relative_to(ROOT)} uses an unpinned external "
                    f"action: {action}"
                )


def require_status_identity(state: dict, version: str) -> None:
    """Keep stable, candidate and stopped-experiment receipts disjoint."""

    verdict = state.get("verdict")
    if not isinstance(verdict, dict):
        fail("PROJECT_STATE.verdict must be an object")

    candidate = verdict.get("active_release_candidate")
    development = state.get("development")
    if not isinstance(development, dict):
        fail("PROJECT_STATE.development must be an object")

    if candidate is None:
        if verdict.get("stable_release") != version:
            fail(
                "no active candidate: metadata must match verdict.stable_release: "
                f"metadata={version!r} stable={verdict.get('stable_release')!r}"
            )
        if development.get("track") != "stable":
            fail("no active candidate: development.track must be stable")
        readme = (ROOT / "README.md").read_text("utf-8")
        if f"你可以安装的稳定版 | **{version}**" not in readme:
            fail("README stable status must match metadata version")
        if "活跃发布候选 | **无**" not in readme:
            fail("README must state that no active release candidate exists")
    elif not isinstance(candidate, dict):
        fail("verdict.active_release_candidate must be null or an object")
    else:
        if str(candidate.get("version")) != version:
            fail("active release candidate must match metadata version")
        if candidate.get("releaseable") is not True:
            fail("an active release candidate must explicitly be releaseable")

    experiments = state.get("closed_experiments", [])
    if not isinstance(experiments, list):
        fail("PROJECT_STATE.closed_experiments must be a list")
    for experiment in experiments:
        if not isinstance(experiment, dict):
            fail("every closed experiment must be an object")
        experiment_id = str(experiment.get("id") or "<missing-id>")
        if experiment.get("releaseable") is not False:
            fail(f"closed experiment {experiment_id} must be releaseable=false")
        if experiment.get("status") not in {
            "stopped_after_failure_limit",
            "historical",
            "superseded",
            "rejected",
            "invalidated",
        }:
            fail(f"closed experiment {experiment_id} has an active-looking status")
        archive = str(experiment.get("archive") or "")
        if not archive.startswith("docs/archive/") or not (ROOT / archive).is_file():
            fail(f"closed experiment {experiment_id} must point to a cold archive")


def require_stable_workflow_identity() -> None:
    """A stable regression workflow must not be repurposed by experiments."""

    stable = ROOT / ".github/workflows/stable-0.1.19-dashboard-regression.yml"
    if not stable.is_file():
        fail("stable 0.1.19 Dashboard regression workflow is missing")
    text = stable.read_text("utf-8")
    if "name: Stable 0.1.19 Dashboard Regression" not in text:
        fail("stable Dashboard workflow identity changed")
    if "browser_matrix_0_1_19.py" not in text:
        fail("stable Dashboard workflow no longer runs the 0.1.19 baseline")
    if "0.1.20" in text or "EXPERIMENT" in text:
        fail("stable Dashboard workflow contains experimental identity")
    if (ROOT / ".github/workflows/probe-real-dashboard-ui.yml").exists():
        fail("ambiguous legacy Dashboard workflow filename must stay retired")


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

    require_status_identity(state, version)

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

    reject_active_release_version_literals()
    require_pinned_external_actions()
    require_stable_workflow_identity()

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
