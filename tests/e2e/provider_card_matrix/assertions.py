"""Structural assertions for provider-card/UI E2E.

These assertions intentionally avoid model-capability conclusions. They verify
ownership, reachability, persistence boundaries, and matrix integrity.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

VIDEO_KEY = "volcengine_video_input_enabled"
VIDEO_UI_PREFIX = "_volcengine_video_transport_ui_"
OWNED_SOURCE_TYPES = {
    "volcengine_ark_chat_completion",
    "volcengine_agent_plan_chat_completion",
}


def assert_matrix_provider_entry(entry: Mapping[str, Any]) -> None:
    required = {"id", "provider_type", "source_type", "owned", "card_paths", "runtime"}
    missing = sorted(required - set(entry))
    if missing:
        raise AssertionError(f"provider matrix entry missing keys: {missing}")

    if not isinstance(entry["id"], str) or not entry["id"].strip():
        raise AssertionError("provider matrix id must be a non-empty string")
    if not isinstance(entry["card_paths"], list):
        raise AssertionError(f"{entry['id']}: card_paths must be a list")
    if not isinstance(entry["runtime"], list):
        raise AssertionError(f"{entry['id']}: runtime must be a list")

    owned = bool(entry["owned"])
    source_type = str(entry["source_type"])
    if owned != (source_type in OWNED_SOURCE_TYPES):
        raise AssertionError(
            f"{entry['id']}: owned={owned} disagrees with source_type={source_type!r}"
        )


def assert_unique_provider_ids(entries: Iterable[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        provider_id = str(entry.get("id") or "")
        if provider_id in seen:
            raise AssertionError(f"duplicate provider matrix id: {provider_id}")
        seen.add(provider_id)


def assert_foreign_config_is_clean(config: Mapping[str, Any]) -> None:
    if VIDEO_KEY in config:
        raise AssertionError("foreign provider contains canonical Volcengine video key")
    leaked = [
        key
        for key in config
        if isinstance(key, str) and key.startswith(VIDEO_UI_PREFIX)
    ]
    if leaked:
        raise AssertionError(f"foreign provider contains temporary Volcengine UI keys: {leaked}")


def assert_no_temporary_ui_keys_persisted(config: Mapping[str, Any]) -> None:
    leaked = [
        key
        for key in config
        if isinstance(key, str) and key.startswith(VIDEO_UI_PREFIX)
    ]
    if leaked:
        raise AssertionError(f"temporary Dashboard UI keys crossed persistence boundary: {leaked}")


def assert_owned_model_card_saved(
    config: Mapping[str, Any],
    *,
    expected_video_enabled: bool,
) -> None:
    assert_no_temporary_ui_keys_persisted(config)
    value = config.get(VIDEO_KEY)
    if value is not expected_video_enabled:
        raise AssertionError(
            f"expected {VIDEO_KEY}={expected_video_enabled!r}, got {value!r}"
        )


def assert_modalities_preserved(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if before.get("modalities") != after.get("modalities"):
        raise AssertionError(
            "plugin migration/save changed AstrBot-owned modalities: "
            f"before={before.get('modalities')!r}, after={after.get('modalities')!r}"
        )


def assert_skip_record(record: Mapping[str, Any]) -> None:
    if record.get("status") != "SKIP":
        return
    reason = str(record.get("reason") or "").strip()
    if not reason:
        raise AssertionError("SKIP result must include a non-empty reason")


def assert_layout_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Validate the stable semantic shape collected from Dashboard.

    The browser harness will populate this structure. This function deliberately
    does not assert pixel geometry because visual screenshots are evidence while
    semantic field ownership/order/grouping are the stable contract.
    """

    required = {
        "provider_type",
        "source_type",
        "card_kind",
        "visible_fields",
        "hidden_fields",
        "field_order",
        "groups",
    }
    missing = sorted(required - set(snapshot))
    if missing:
        raise AssertionError(f"layout snapshot missing keys: {missing}")

    visible = snapshot["visible_fields"]
    hidden = snapshot["hidden_fields"]
    order = snapshot["field_order"]
    groups = snapshot["groups"]
    if not all(isinstance(value, list) for value in (visible, hidden, order)):
        raise AssertionError("visible_fields/hidden_fields/field_order must be lists")
    if not isinstance(groups, dict):
        raise AssertionError("groups must be an object")

    duplicates = [field for field in visible if visible.count(field) > 1]
    if duplicates:
        raise AssertionError(f"duplicate visible fields in layout snapshot: {sorted(set(duplicates))}")

    source_type = str(snapshot["source_type"])
    if source_type not in OWNED_SOURCE_TYPES:
        if VIDEO_KEY in visible or any(
            isinstance(field, str) and field.startswith(VIDEO_UI_PREFIX)
            for field in visible
        ):
            raise AssertionError("foreign provider layout exposes Volcengine video UI")


def assert_runtime_result_record(record: Mapping[str, Any]) -> None:
    required = {"provider_id", "scenario", "status"}
    missing = sorted(required - set(record))
    if missing:
        raise AssertionError(f"runtime result missing keys: {missing}")

    status = record["status"]
    if status not in {"PASS", "FAIL", "SKIP", "OBSERVED"}:
        raise AssertionError(f"unknown runtime status: {status!r}")
    assert_skip_record(record)

    # An observation may record upstream acceptance/rejection or transport
    # provenance. It must not silently masquerade as a capability verdict.
    if "capability_verdict" in record:
        raise AssertionError(
            "provider-card E2E result must record observation/provenance, not permanent capability_verdict"
        )
