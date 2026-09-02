#!/usr/bin/env python3
"""Current release topology and observable-product gate integrity checks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CURRENT_UI = "tests/e2e/provider_card_matrix/current_release_ui_contract.py"
CURRENT_LIFECYCLE = "tests/e2e/provider_card_matrix/current_lifecycle_contract.py"
HOSTS = ("4.27.3", "4.27.4", "4.28.0-beta.1")
WORKFLOWS = {"model-card-video-contract.yml", "model-card-lifecycle-contract.yml"}
E2E_FILES = {
    "README.md",
    "assertions.py",
    "browser_matrix.py",
    "model_card_browser_core.py",
    "lifecycle_browser_core.py",
    "current_release_ui_contract.py",
    "current_lifecycle_contract.py",
    "foreign_scope_matrix.py",
}

FORBIDDEN_PATHS = (
    "capabilities/video_modality_fallback.py",
    "docs/archive",
    "docs/contracts/ROBUST_VIDEO_FALLBACK_0_1_23.md",
    "docs/ADR/ADR-0005-knowledge-lifecycle-and-drift-control.md",
    "tests/test_0_1_15_feedback_boundary.py",
    "tests/test_0_1_19_model_fields.py",
    "tests/test_0_1_19_model_fields_ui.py",
    "tests/test_0_1_19_provider_overrides.py",
    "tests/test_0_1_20_dashboard_asset_scope.py",
    "tests/test_0_1_23_video_delivery_fallback.py",
    "tests/test_model_card_ui_scope.py",
)

WARM = (
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "docs/PROJECT_STATE.json",
    "docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md",
    "docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md",
    "docs/AI_ONBOARDING.md",
    "docs/AI_RULES.md",
    "docs/KNOWLEDGE_LIFECYCLE.md",
    "docs/DECISION_INDEX.json",
    "docs/DESIGN_DECISIONS.md",
    "docs/RELEASE_BOUNDARY.md",
)

STALE_MARKERS = (
    "/tree/runtime",
    "archive/model-card-video-known-good",
    "video_modality_fallback.py",
)

DEAD_REGISTRY_MARKERS = (
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
        fail(f"retired/version-authority debris still tracked: {present}")

    workflows_dir = ROOT / ".github" / "workflows"
    actual_workflows = {path.name for path in workflows_dir.glob("*.yml")}
    if actual_workflows != WORKFLOWS:
        fail(f"active workflows must be exactly {sorted(WORKFLOWS)}, got {sorted(actual_workflows)}")

    e2e_dir = ROOT / "tests" / "e2e" / "provider_card_matrix"
    actual_e2e = {path.name for path in e2e_dir.iterdir() if path.is_file()}
    if actual_e2e != E2E_FILES:
        fail(f"active provider-card E2E surface drifted: {sorted(actual_e2e)}")

    state = json.loads((ROOT / "docs" / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    verdict = state.get("verdict") or {}
    if verdict.get("safe_install_branch") != "main" or verdict.get("safe_development_branch") != "main":
        fail("main must be the only durable install/development authority")
    real_ui = state.get("real_ui_contract") or {}
    if real_ui.get("entrypoint") != CURRENT_UI or real_ui.get("lifecycle_entrypoint") != CURRENT_LIFECYCLE:
        fail("PROJECT_STATE does not point at the current browser contracts")
    if tuple(real_ui.get("hosts") or ()) != HOSTS:
        fail(f"real UI host matrix must be exactly {HOSTS!r}")
    if real_ui.get("success_definition") != "observable user-visible model-card state and persistence":
        fail("release success definition is not observable user-visible persistence")

    for relative in WARM:
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing current authority/navigation file: {relative}")
        text = path.read_text(encoding="utf-8")
        for marker in STALE_MARKERS:
            if marker in text:
                fail(f"{relative} still contains stale current marker {marker!r}")

    index = json.loads((ROOT / "docs" / "DECISION_INDEX.json").read_text(encoding="utf-8"))
    history = index.get("history") or {}
    if history.get("deep_history") != "Git commit history" or history.get("current_tree_failed_state_archive") is not False:
        fail("history policy must use Git history with no current-tree failed-state archive")

    release_workflow = (workflows_dir / "model-card-video-contract.yml").read_text(encoding="utf-8")
    lifecycle_workflow = (workflows_dir / "model-card-lifecycle-contract.yml").read_text(encoding="utf-8")
    for host in HOSTS:
        if host not in release_workflow or host not in lifecycle_workflow:
            fail(f"workflow matrix missing host {host}")
    if CURRENT_UI not in release_workflow or "foreign_scope_matrix.py" not in release_workflow:
        fail("release workflow is not wired to current UI + foreign isolation")
    if CURRENT_LIFECYCLE not in lifecycle_workflow:
        fail("lifecycle workflow is not wired to current lifecycle contract")

    current_ui = (ROOT / CURRENT_UI).read_text(encoding="utf-8")
    for term in ("custom_extra_body", "expected_checked=False", "baseline.run_case"):
        if term not in current_ui:
            fail(f"current UI entrypoint lost proof hook {term}")

    core = (e2e_dir / "model_card_browser_core.py").read_text(encoding="utf-8")
    for term in ("await enable_video_modality(create_dialog)", "expected_checked=True", "await save_model_dialog(create_dialog)"):
        if term not in core:
            fail(f"browser core lost visible click/save persistence proof {term}")

    lifecycle = (ROOT / CURRENT_LIFECYCLE).read_text(encoding="utf-8")
    if "custom_extra_body" not in lifecycle or "expected_video_checked=True" not in lifecycle:
        fail("lifecycle contract no longer proves checked Video + native custom body")

    registry = (ROOT / "registry.py").read_text(encoding="utf-8")
    for marker in DEAD_REGISTRY_MARKERS:
        if marker in registry:
            fail(f"registry still contains retired Source-page Video infrastructure: {marker}")
    for required in ("normalize_owned_model_card_for_save", "ProviderConfigService.create_provider", "ProviderConfigService.update_provider"):
        if required not in registry:
            fail(f"registry lost current owned-card save boundary: {required}")

    print("SINGLE_TRUTH_OK main_only=1 workflows=2 e2e_current_only=1 real_ui_gate=1 hosts=" + ",".join(HOSTS))


if __name__ == "__main__":
    main()
