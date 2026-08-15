#!/usr/bin/env python3
"""Fail release preparation when documentation authority drifts.

This intentionally checks only HOT-authority consistency. Historical documents
may contain older versions and completed goals without failing this guard.
"""

from __future__ import annotations

import json
import re
import sys
import argparse
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


def require_readme_status_projection(state: dict, version: str) -> None:
    """Prevent the human status table from drifting away from HOT state."""

    readme = (ROOT / "README.md").read_text("utf-8")
    stable = str(state["verdict"].get("stable_release") or "")
    candidate = state["verdict"].get("active_release_candidate")
    if f"version-{version}" not in readme:
        fail("README version badge must match metadata version")
    if f"| 你可以安装的稳定版 | **{stable}**" not in readme:
        fail("README stable version must match PROJECT_STATE")
    if candidate is None:
        if "| 活跃发布候选 | **无**" not in readme:
            fail("README must state that no release candidate exists")
    elif f"| 活跃发布候选 | **{candidate.get('version')}**" not in readme:
        fail("README candidate version must match PROJECT_STATE")
    marketplace = state["verdict"].get("marketplace")
    if isinstance(marketplace, dict) and marketplace.get("status") == "package_identity_mismatch":
        listed = marketplace.get("listed_version")
        expected = (
            f"版本页显示 **v{listed} Published**，但冻结下载包与稳定 `runtime` 不一致"
        )
        if expected not in readme:
            fail("README must expose the observed marketplace package mismatch")


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
    """Keep stable, development, candidate and experiment identities disjoint."""

    verdict = state.get("verdict")
    if not isinstance(verdict, dict):
        fail("PROJECT_STATE.verdict must be an object")

    candidate = verdict.get("active_release_candidate")
    experiment = state.get("active_experiment")
    development = state.get("development")
    if not isinstance(development, dict):
        fail("PROJECT_STATE.development must be an object")

    if candidate is not None and experiment is not None:
        fail("active release candidate and active experiment cannot coexist")

    readme = (ROOT / "README.md").read_text("utf-8")
    if candidate is None and experiment is None:
        if verdict.get("stable_release") != version:
            fail(
                "no active candidate: metadata must match verdict.stable_release: "
                f"metadata={version!r} stable={verdict.get('stable_release')!r}"
            )
        if development.get("track") != "stable":
            fail("no active candidate: development.track must be stable")
        if f"你可以安装的稳定版 | **{version}**" not in readme:
            fail("README stable status must match metadata version")
        if "活跃发布候选 | **无**" not in readme:
            fail("README must state that no active release candidate exists")
    elif experiment is not None:
        if not isinstance(experiment, dict):
            fail("active_experiment must be null or an object")
        if str(experiment.get("version")) != version:
            fail("active experiment must match metadata version")
        if experiment.get("releaseable") is not False:
            fail("an active experiment must explicitly be releaseable=false")
        if development.get("track") != "experiment":
            fail("active experiment requires development.track=experiment")
        if str(experiment.get("status")) not in {"active", "validating"}:
            fail("active experiment must have active or validating status")
    elif not isinstance(candidate, dict):
        fail("verdict.active_release_candidate must be null or an object")
    else:
        if str(candidate.get("version")) != version:
            fail("active release candidate must match metadata version")
        if development.get("track") != "release_candidate":
            fail("active release candidate requires development.track=release_candidate")
        status = str(candidate.get("status") or "")
        releaseable = candidate.get("releaseable")
        if status == "validating" and releaseable is not False:
            fail("a validating release candidate must be releaseable=false")
        if status == "ready" and releaseable is not True:
            fail("a ready release candidate must be releaseable=true")
        if status not in {"validating", "ready"}:
            fail("active release candidate status must be validating or ready")

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
    """The 0.1.19 compatibility baseline must not be repurposed by experiments."""

    stable = ROOT / ".github/workflows/compatibility-baseline-0.1.19-dashboard.yml"
    if not stable.is_file():
        fail("stable 0.1.19 Dashboard regression workflow is missing")
    text = stable.read_text("utf-8")
    if "name: 0.1.19 Compatibility Baseline Dashboard Regression" not in text:
        fail("0.1.19 compatibility baseline workflow identity changed")
    if "browser_matrix_0_1_19.py" not in text:
        fail("stable Dashboard workflow no longer runs the 0.1.19 baseline")
    if "0.1.20" in text or "EXPERIMENT" in text:
        fail("stable Dashboard workflow contains experimental identity")
    if (ROOT / ".github/workflows/probe-real-dashboard-ui.yml").exists():
        fail("ambiguous legacy Dashboard workflow filename must stay retired")


def require_no_active_paid_probes() -> None:
    """Exact retired side-effect workflows must not return as live controls.

    Do not turn provider names, endpoints, or secret-variable names into global
    forbidden words: an explicitly authorised future test may legitimately use
    them.  Lifecycle is attached to a concrete workflow identity instead.
    """

    retired_workflows = {
        "real-volcengine-runtime-matrix.yml",
        "seedance-chat-transfer-test.yml",
        "seedance-image-to-video-test.yml",
        "seedance-model-controlled-probe.yml",
        "seedance-pro-250528-i2v-probe.yml",
        "seedance-qqshow-smug-sticker.yml",
        "seedance-remaining-models-probe.yml",
    }
    present = sorted(
        name for name in retired_workflows
        if (ROOT / ".github/workflows" / name).exists()
    )
    if present:
        fail(f"retired external-effect workflows returned: {present}")


def require_decision_lifecycle(state: dict) -> None:
    """Completed decisions stay inert; live decisions must be named by HOT state."""

    decision_root = ROOT / "governance/decisions"
    completed_ids = {f"D-{number:03d}" for number in range(1, 7)}
    goal = state.get("current_goal")
    active_ids = set(goal.get("active_decision_ids", [])) if isinstance(goal, dict) else set()
    for path in sorted(decision_root.glob("D-*.json")):
        try:
            record = json.loads(path.read_text("utf-8"))
        except Exception as exc:
            fail(f"invalid governance decision JSON in {path.relative_to(ROOT)}: {exc}")
        lifecycle = record.get("lifecycle")
        if not isinstance(lifecycle, dict):
            fail(f"{path.relative_to(ROOT)} must declare lifecycle")
        status = str(lifecycle.get("status") or "")
        decision_id = str(record.get("decision_id") or "")
        if decision_id in completed_ids:
            if not status.startswith("completed_"):
                fail(f"{path.relative_to(ROOT)} must remain completed")
            if lifecycle.get("action_authority") != "none":
                fail(f"{path.relative_to(ROOT)} must not authorize new actions")
        elif status.startswith("completed_"):
            if lifecycle.get("action_authority") != "none":
                fail(f"{path.relative_to(ROOT)} completed decision must be inert")
        elif decision_id not in active_ids:
            fail(
                f"{path.relative_to(ROOT)} is active-looking but is not named in "
                "PROJECT_STATE.current_goal.active_decision_ids"
            )


def require_cold_evidence_markers() -> None:
    """A superseded pre-probe snapshot must announce that fact before details."""

    relative = "evidence/model-objective-conditions.md"
    text = (ROOT / relative).read_text("utf-8")
    opening = "\n".join(text.splitlines()[:8])
    for marker in (
        "historical pre-probe snapshot",
        "Lifecycle: COLD / non-action-driving",
        "strategy/executable-model-graph-v0.2.json",
        "docs/PROJECT_STATE.json",
    ):
        if marker not in opening:
            fail(f"{relative} must expose cold lifecycle marker: {marker}")

    architecture = "docs/comparable-architectures.md"
    architecture_opening = "\n".join(
        (ROOT / architecture).read_text("utf-8").splitlines()[:8]
    )
    for marker in (
        "Lifecycle: COLD historical research",
        "docs/PROJECT_STATE.json",
        "no authority to create workflows",
    ):
        if marker not in architecture_opening:
            fail(f"{architecture} must expose cold lifecycle marker: {marker}")

    duplicate_assets = (
        "assets/seedance_test/qqshow_smug_reference.jpg",
        "assets/seedance_tests/qqshow_smug_frame_20260812.jpg",
    )
    present = [path for path in duplicate_assets if (ROOT / path).exists()]
    if present:
        fail(f"unreferenced duplicate Seedance assets returned: {present}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-releaseable",
        action="store_true",
        help="also require a ready release candidate for publication",
    )
    parser.add_argument(
        "--allow-no-candidate",
        action="store_true",
        help=(
            "treat an absent active release candidate as a verified "
            "publication no-op (steady post-release state)"
        ),
    )
    args = parser.parse_args()
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
    require_readme_status_projection(state, version)

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
    require_no_active_paid_probes()
    require_decision_lifecycle(state)
    require_cold_evidence_markers()

    if not (ROOT / "docs/archive/README.md").is_file():
        fail("docs/archive/README.md is required for explicit cold-zone semantics")
    if not (ROOT / "docs/archive/PROJECT_STATE-0.1.18.md").is_file():
        fail("0.1.18 completed HOT frontier must remain demoted in docs/archive")

    old_graph = read_json("strategy/executable-model-graph-v0.1.json")
    new_graph = read_json("strategy/executable-model-graph-v0.2.json")
    prompt_registry = read_json("strategy/prompt-handle-registry-v0.1.json")
    old_lifecycle = old_graph.get("lifecycle")
    new_lifecycle = new_graph.get("lifecycle")
    if not isinstance(old_lifecycle, dict) or old_lifecycle.get("status") != "superseded":
        fail("strategy v0.1 must be explicitly superseded")
    if old_lifecycle.get("superseded_by") != "strategy/executable-model-graph-v0.2.json":
        fail("strategy v0.1 must identify v0.2 as its successor")
    if not isinstance(new_lifecycle, dict) or new_lifecycle.get("status") not in {"warm", "active"}:
        fail("strategy v0.2 must identify an explicit non-superseded lifecycle state")
    prompt_lifecycle = prompt_registry.get("lifecycle")
    if not isinstance(prompt_lifecycle, dict):
        fail("prompt handle registry must declare its own lifecycle")
    if prompt_lifecycle.get("status") != "warm":
        fail("prompt handle registry must remain a warm evidence reference")
    if prompt_lifecycle.get("action_authority") != "none":
        fail("prompt handle registry must not authorize actions")
    if prompt_lifecycle.get("current_state_source") != "docs/PROJECT_STATE.json":
        fail("prompt handle registry must point to HOT project state")

    if args.require_releaseable:
        candidate = state["verdict"].get("active_release_candidate")
        if not isinstance(candidate, dict):
            if args.allow_no_candidate:
                # Steady post-release state: nothing to publish. All consistency
                # checks above already passed; the publisher's tree comparison
                # still rejects any changed runtime tree without a new candidate.
                print(
                    "KNOWLEDGE_STATE_OK no active release candidate; "
                    "publication is a no-op for an unchanged runtime tree"
                )
                return 0
            fail("publication requires an active release candidate")
        if candidate.get("status") != "ready" or candidate.get("releaseable") is not True:
            fail("publication requires candidate status=ready and releaseable=true")

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
