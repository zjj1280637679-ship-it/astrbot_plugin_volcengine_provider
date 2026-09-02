#!/usr/bin/env python3
"""Reject obsolete release topology, dead Source-UI infrastructure and stale guidance."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CURRENT_UI_ENTRYPOINT = "tests/e2e/provider_card_matrix/current_release_ui_contract.py"
CURRENT_LIFECYCLE_ENTRYPOINT = "tests/e2e/provider_card_matrix/current_lifecycle_contract.py"
REQUIRED_HOSTS = ("4.27.3", "4.27.4", "4.28.0-beta.1")
CURRENT_WORKFLOWS = {
    "model-card-video-contract.yml",
    "model-card-lifecycle-contract.yml",
}

FORBIDDEN_PATHS = (
    ".github/workflows/compatibility-baseline-0.1.19-dashboard.yml",
    ".github/workflows/renderer-boundary-diagnostic.yml",
    ".github/workflows/real-cross-provider-effect-matrix.yml",
    ".github/workflows/real-deepseek-foreign-differential.yml",
    ".github/workflows/real-deepseek-model-fetch.yml",
    ".github/workflows/real-source-type-video-differential.yml",
    "capabilities/video_modality_fallback.py",
    "docs/archive/EXPERIMENT-0.1.20-source-scoped-video.md",
    "docs/archive/PROJECT_STATE-0.1.18.md",
    "docs/archive/README.md",
    "docs/ADR/ADR-0005-knowledge-lifecycle-and-drift-control.md",
    "docs/contracts/ROBUST_VIDEO_FALLBACK_0_1_23.md",
    "tests/e2e/provider_card_matrix/browser_matrix_0_1_24_contract.py",
    "tests/e2e/provider_card_matrix/lifecycle_matrix_0_1_24_stable.py",
    "tests/test_0_1_20_dashboard_asset_scope.py",
    "tests/test_0_1_23_video_delivery_fallback.py",
    "tests/test_model_card_ui_scope.py",
)

AUTHORITATIVE_OR_WARM = (
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/AI_ONBOARDING.md",
    "docs/AI_RULES.md",
    "docs/KNOWLEDGE_LIFECYCLE.md",
    "docs/DESIGN_DECISIONS.md",
    "docs/DECISION_INDEX.json",
    "docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md",
    "docs/RELEASE_BOUNDARY.md",
    "docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md",
    "docs/ADR/ADR-0003-dashboard-schema-isolation.md",
    "docs/ADR/ADR-0004-migration-preserves-intent.md",
    "docs/PROJECT_STATE.json",
)

# These markers are unambiguously stale even when read in context. Do not use
# broad forbidden words for concepts that a current rule may legitimately negate.
STALE_CURRENT_MARKERS = (
    "/tree/runtime",
    "archive/model-card-video-known-good",
    "video_modality_fallback.py",
    "0.1.18 Source presentation control remains",
    "stable 0.1.18/0.1.19 Source UI remains",
)

DEAD_REGISTRY_SOURCE_UI_MARKERS = (
    "can_install_source_video_ui",
    "source_upsert_wrapper",
    "_apply_source_video_ui_settings",
    "_inject_owned_source_transport_hint",
    "_SOURCE_UPSERT_WRAPPER",
    "_SOURCE_UPSERT_ORIGINAL",
)


def fail(message: str) -> None:
    raise SystemExit(f"SINGLE_TRUTH_ERROR: {message}")


def main() -> None:
    present = [path for path in FORBIDDEN_PATHS if (ROOT / path).exists()]
    if present:
        fail(f"retired release/fallback/source-UI infrastructure is still tracked: {present}")
    if (ROOT / "docs" / "archive").exists():
        fail("current tree must not contain a failed-state archive directory")

    workflows_dir = ROOT / ".github" / "workflows"
    actual_workflows = {path.name for path in workflows_dir.glob("*.yml")}
    if actual_workflows != CURRENT_WORKFLOWS:
        fail(
            "active Actions surface must be exactly the current model-card and lifecycle gates; "
            f"got {sorted(actual_workflows)}"
        )

    for path in (CURRENT_UI_ENTRYPOINT, CURRENT_LIFECYCLE_ENTRYPOINT):
        if not (ROOT / path).is_file():
            fail(f"missing current release acceptance entrypoint: {path}")

    state_path = ROOT / "docs" / "PROJECT_STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    verdict = state.get("verdict") or {}
    if verdict.get("safe_install_branch") != "main":
        fail("PROJECT_STATE.safe_install_branch must be main")
    if verdict.get("safe_development_branch") != "main":
        fail("PROJECT_STATE.safe_development_branch must be main")

    real_ui = state.get("real_ui_contract") or {}
    if real_ui.get("entrypoint") != CURRENT_UI_ENTRYPOINT:
        fail("PROJECT_STATE real UI entrypoint is not the current contract")
    if real_ui.get("lifecycle_entrypoint") != CURRENT_LIFECYCLE_ENTRYPOINT:
        fail("PROJECT_STATE lifecycle entrypoint is not the current contract")
    if tuple(real_ui.get("hosts") or ()) != REQUIRED_HOSTS:
        fail(f"PROJECT_STATE real UI hosts must be exactly {REQUIRED_HOSTS!r}")
    if real_ui.get("success_definition") != "observable user-visible model-card state and persistence":
        fail("release success definition has drifted away from observable UI persistence")

    for relative in AUTHORITATIVE_OR_WARM:
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing current authority/navigation file: {relative}")
        text = path.read_text(encoding="utf-8")
        for marker in STALE_CURRENT_MARKERS:
            if marker in text:
                fail(f"{relative} still contains stale current guidance marker {marker!r}")

    decision_index = json.loads((ROOT / "docs" / "DECISION_INDEX.json").read_text(encoding="utf-8"))
    history = decision_index.get("history") or {}
    if history.get("current_tree_failed_state_archive") is not False:
        fail("DECISION_INDEX must declare no current-tree failed-state archive")
    if history.get("deep_history") != "Git commit history":
        fail("deep history must resolve to Git commit history, not an alternate file tree")

    video_workflow = (workflows_dir / "model-card-video-contract.yml").read_text(encoding="utf-8")
    lifecycle_workflow = (workflows_dir / "model-card-lifecycle-contract.yml").read_text(encoding="utf-8")
    if CURRENT_UI_ENTRYPOINT not in video_workflow:
        fail("model-card workflow is not wired to the current real UI contract")
    if CURRENT_LIFECYCLE_ENTRYPOINT not in lifecycle_workflow:
        fail("lifecycle workflow is not wired to the current lifecycle contract")
    for host in REQUIRED_HOSTS:
        if host not in video_workflow:
            fail(f"model-card workflow is missing host {host}")
        if host not in lifecycle_workflow:
            fail(f"lifecycle workflow is missing host {host}")

    current_ui = (ROOT / CURRENT_UI_ENTRYPOINT).read_text(encoding="utf-8")
    for term in ("custom_extra_body", "expected_checked=False", "baseline.assert_video_modality_scope", "baseline.run_case"):
        if term not in current_ui:
            fail(f"current real UI contract is missing required proof hook: {term}")

    baseline_ui = (ROOT / "tests" / "e2e" / "provider_card_matrix" / "browser_matrix_0_1_19.py").read_text(encoding="utf-8")
    for term in ("await enable_video_modality(create_dialog)", "expected_checked=True", "await save_model_dialog(create_dialog)"):
        if term not in baseline_ui:
            fail(f"real browser implementation lost visible Video click/persistence proof: {term}")

    lifecycle = (ROOT / CURRENT_LIFECYCLE_ENTRYPOINT).read_text(encoding="utf-8")
    if "custom_extra_body" not in lifecycle or "expected_video_checked=True" not in lifecycle:
        fail("current lifecycle contract no longer proves request-row visibility and checked Video")

    registry = (ROOT / "registry.py").read_text(encoding="utf-8")
    for marker in DEAD_REGISTRY_SOURCE_UI_MARKERS:
        if marker in registry:
            fail(f"registry still carries retired Source-page Video infrastructure: {marker}")
    for required in (
        "normalize_owned_model_card_for_save",
        "ProviderConfigService.create_provider",
        "ProviderConfigService.update_provider",
        "_inject_model_card_video_control",
    ):
        if required not in registry:
            fail(f"registry lost current owned-card persistence boundary: {required}")

    model_scope = (ROOT / "capabilities" / "model_scope.py").read_text(encoding="utf-8")
    if '"video" in modalities' not in model_scope or "VIDEO_CONTROLS_VISIBLE_KEY" not in model_scope:
        fail("current owned-card save/migration boundary is missing native Video + legacy cleanup logic")

    print("SINGLE_TRUTH_OK main_only=1 workflows=2 dead_source_ui=0 failed_state_archive=0 stale_current_guidance=0 real_ui_gate=1 hosts=" + ",".join(REQUIRED_HOSTS))


if __name__ == "__main__":
    main()
