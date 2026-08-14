"""Reversible Dashboard adaptation for source-scoped model-card fields.

AstrBot 4.27 exposes three different frontend objects whose meanings must remain
separate for this plugin feature to be correct:

* ``providerModelConfigSchema`` is a private metadata clone created only after the
  currently selected Provider Source type is known. For Ark / Agent Plan model
  cards, that clone may gain one native ``video`` option and may reveal the lower
  Volcengine-owned bilingual request-row metadata. Foreign clones must keep the
  host modalities metadata untouched and those plugin rows hidden.
* ``buildModelProviderConfig(modelName)`` creates the concrete data object used as
  ``AstrBotConfig.iterable`` for a newly added model card. AstrBot renders only
  keys that already exist on that concrete object, so an owned new card must also
  receive the lower Volcengine request-field values needed to instantiate those
  rows; foreign new cards must not receive those keys at all.
* ``ConfigItemRenderer`` owns the host translation path for checkbox labels. The
  plugin must not replace AstrBot's first four modality labels merely to name its
  fifth option. Instead, the owned private modalities clone carries a transient
  marker, and the renderer supplies a plugin-localized label only when the host
  translated label array has no element for the added ``video`` index.

All three structural boundaries must occur exactly once in the same served
Dashboard asset before any transformation is accepted. This prevents a partial
patch in which one concrete object changes while another required object remains
unadapted. The original AstrBot asset is never modified on disk.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .model_fields import MODEL_FIELD_SCHEMA
from .model_scope import OWNED_SOURCE_TYPES

_PATCH_MARKER = "/*astrbot-volcengine-model-dialog-v4*/"
_VIDEO_LABEL_FALLBACK_MARKER = "__astrbot_volcengine_video_label_fallback"
_DASHBOARD_ASSET_LEASE_COUNT = 0
_RESOLVE_WRAPPER: Callable[..., Any] | None = None
_RESOLVE_ORIGINAL: Callable[..., Any] | None = None
_INDEX_WRAPPER: Callable[..., Any] | None = None
_INDEX_ORIGINAL: Callable[..., Any] | None = None
_CACHE_ROOT: Path | None = None
_CACHE: dict[Path, Path] = {}
_INDEX_CACHE: dict[Path, Path] = {}
_MISSES: set[Path] = set()
_STATIC_FOLDER_ASSETS: dict[Path, Path | None] = {}
_LOCK = threading.RLock()

_MODEL_DIALOG_BOUNDARY = re.compile(
    r'(?P<source_type>[A-Za-z_$][\w$]*)\s*===\s*"googlegenai_chat_completion"'
    r'[\s\S]{0,320}?'
    r'(?P<hidden>[A-Za-z_$][\w$]*)\.push\(\s*"custom_extra_body"\s*\)\s*;?'
    r'[\s\S]{0,320}?'
    r'for\s*\(\s*const\s+(?P<item>[A-Za-z_$][\w$]*)\s+of\s+(?P=hidden)\s*\)\s*\{?\s*'
    r'(?P<schema>[A-Za-z_$][\w$]*)\.provider\.items\[(?P=item)\]'
)

_MODEL_BUILDER_BOUNDARY = re.compile(
    r'function\s+(?P<builder>[A-Za-z_$][\w$]*)\((?P<model>[A-Za-z_$][\w$]*)\)\{'
    r'(?P<body>[\s\S]{0,2200}?'
    r'const\s+(?P<source_id>[A-Za-z_$][\w$]*)\s*=\s*\(\('
    r'(?P<tmp>[A-Za-z_$][\w$]*)\s*=\s*(?P<selected>[A-Za-z_$][\w$]*)\.value\)'
    r'\s*==\s*null\s*\?\s*void\s+0\s*:\s*(?P=tmp)\.id\)\s*\|\|'
    r'[\s\S]{0,1500}?'
    r'return\s*(?:\([^{};]{0,500}?,\s*)?\{'
    r'id\s*:\s*(?P<id_expr>[A-Za-z_$][\w$]*)\s*,'
    r'enable\s*:\s*!0\s*,'
    r'provider_source_id\s*:\s*(?P=source_id)\s*,'
    r'model\s*:\s*(?P=model)\s*,'
    r'modalities\s*:\s*(?P<modalities>[A-Za-z_$][\w$]*)\s*,'
    r'custom_extra_body\s*:\s*\{\}\s*,'
    r'max_context_tokens\s*:\s*(?P<context>[A-Za-z_$][\w$]*)\s*,'
    r'reasoning\s*:\s*(?P<reasoning>[A-Za-z_$][\w$]*\([^{};]*?\))'
    r'(?P<object_close>\})'
    r')'
)

_RENDERER_LABEL_BOUNDARY = re.compile(
    r'function\s+(?P<label_fn>[A-Za-z_$][\w$]*)\s*\('
    r'(?P<meta>[A-Za-z_$][\w$]*)\s*,'
    r'(?P<index>[A-Za-z_$][\w$]*)\s*,'
    r'(?P<option>[A-Za-z_$][\w$]*)\s*\)\s*\{\s*'
    r'const\s+(?P<labels>[A-Za-z_$][\w$]*)\s*=\s*'
    r'(?P<translated>[A-Za-z_$][\w$]*)\s*\(\s*(?P=meta)\s*\)\s*;\s*'
    r'return\s+(?P=labels)\s*\?\s*(?P=labels)\s*\[\s*(?P=index)\s*\]\s*'
    r':\s*(?P=option)\s*\}'
)

_NEW_CARD_DEFAULTS: dict[str, Any] = {
    "volcengine_video_input_profile": "original",
    "volcengine_reasoning_mode": "",
    "volcengine_reasoning_effort": "",
    "volcengine_temperature": "",
    "volcengine_top_p": "",
    "volcengine_max_output_tokens": "",
    "volcengine_stop_sequences": [],
    "volcengine_frequency_penalty": "",
    "volcengine_presence_penalty": "",
}


def _dialog_adaptation_javascript(*, source_type: str, schema: str) -> str:
    """Adapt only the selected Source's private model-card metadata clone."""

    owned_types = json.dumps(sorted(OWNED_SOURCE_TYPES), ensure_ascii=False)
    plugin_fields = json.dumps(sorted(MODEL_FIELD_SCHEMA), ensure_ascii=False)
    marker = json.dumps(_VIDEO_LABEL_FALLBACK_MARKER, ensure_ascii=False)
    return (
        _PATCH_MARKER
        + f"const __abVolcOwned={owned_types}.includes({source_type});"
        + f"const __abVolcModalities={schema}.provider.items.modalities;"
        + f"const __abVolcPluginFields={plugin_fields};"
        + "if(__abVolcOwned){"
        + "for(const __abVolcKey of __abVolcPluginFields){"
        + f"const __abVolcField={schema}.provider.items[__abVolcKey];"
        + "if(__abVolcField)__abVolcField.invisible=false;"
        + "}"
        + "if(__abVolcModalities){"
        + "const __abVolcOptions=Array.isArray(__abVolcModalities.options)"
        + "?__abVolcModalities.options:[];"
        + "if(!__abVolcOptions.includes(\"video\"))"
        + "__abVolcModalities.options=[...__abVolcOptions,\"video\"];"
        + f"__abVolcModalities[{marker}]=true;"
        + "}"
        + "}else{"
        + "for(const __abVolcKey of __abVolcPluginFields){"
        + f"const __abVolcField={schema}.provider.items[__abVolcKey];"
        + "if(__abVolcField)__abVolcField.invisible=true;"
        + "}"
        + "}"
    )


def _builder_object_insertion(*, selected_source_ref: str) -> str:
    """Instantiate lower request-row keys only on an owned new-card data object."""

    owned_types = json.dumps(sorted(OWNED_SOURCE_TYPES), ensure_ascii=False)
    defaults = json.dumps(_NEW_CARD_DEFAULTS, ensure_ascii=False, separators=(",", ":"))
    return (
        ",...(("
        + f"{selected_source_ref}.value"
        + ")&&"
        + f"{owned_types}.includes({selected_source_ref}.value.type)"
        + f"?{defaults}:{{}})"
    )


def _renderer_label_replacement(match: re.Match[str]) -> str:
    """Preserve host labels and supply only the owned Video index fallback."""

    label_fn = match.group("label_fn")
    meta = match.group("meta")
    index = match.group("index")
    option = match.group("option")
    labels = match.group("labels")
    translated = match.group("translated")
    marker = json.dumps(_VIDEO_LABEL_FALLBACK_MARKER, ensure_ascii=False)
    return (
        f"function {label_fn}({meta},{index},{option}){{"
        f"const {labels}={translated}({meta});"
        f"if({labels}&&{labels}[{index}]!==void 0)return {labels}[{index}];"
        f"if({meta}&&{meta}[{marker}]===true&&{option}===\"video\"){{"
        "const __abVolcLocale=(globalThis.localStorage?.getItem?.(\"astrbot-locale\")||\"zh-CN\").toLowerCase();"
        "return __abVolcLocale.startsWith(\"zh\")?\"视频\":"
        "(__abVolcLocale.startsWith(\"ru\")?\"Видео\":\"Video\");"
        "}"
        f"return {option}"
        "}"
    )


def transform_dashboard_javascript(source: str) -> tuple[str, int]:
    """Return status 1 only for one complete three-object compatible asset.

    ``1`` means the private model-card metadata clone, concrete new-card data
    builder, and host checkbox-label helper are each uniquely known in the same
    asset. ``0`` means at least one required object is absent while none is
    ambiguous. ``>=2`` means at least one required boundary is ambiguous.
    """

    if _PATCH_MARKER in source:
        return source, 1

    dialog_matches = list(_MODEL_DIALOG_BOUNDARY.finditer(source))
    builder_matches = list(_MODEL_BUILDER_BOUNDARY.finditer(source))
    renderer_matches = list(_RENDERER_LABEL_BOUNDARY.finditer(source))
    counts = (len(dialog_matches), len(builder_matches), len(renderer_matches))
    if counts != (1, 1, 1):
        if all(count <= 1 for count in counts):
            return source, 0
        return source, max(2, sum(counts))

    dialog = dialog_matches[0]
    builder = builder_matches[0]
    renderer = renderer_matches[0]

    dialog_insertion = _dialog_adaptation_javascript(
        source_type=dialog.group("source_type"),
        schema=dialog.group("schema"),
    )
    relative_for = re.search(r'for\s*\(', dialog.group(0))
    if relative_for is None:
        return source, 0
    dialog_offset = dialog.start() + relative_for.start()

    builder_offset = builder.start("object_close")
    builder_insertion = _builder_object_insertion(
        selected_source_ref=builder.group("selected"),
    )
    renderer_replacement = _renderer_label_replacement(renderer)

    edits = [
        (dialog_offset, dialog_offset, dialog_insertion),
        (builder_offset, builder_offset, builder_insertion),
        (renderer.start(), renderer.end(), renderer_replacement),
    ]
    transformed = source
    for start, end, replacement in sorted(edits, key=lambda item: item[0], reverse=True):
        transformed = transformed[:start] + replacement + transformed[end:]
    return transformed, 1


def _cache_root() -> Path:
    global _CACHE_ROOT
    if _CACHE_ROOT is None:
        _CACHE_ROOT = Path(tempfile.mkdtemp(prefix="astrbot-volcengine-dashboard-"))
    return _CACHE_ROOT


def _select_compatible_asset(static_folder: str | Path | None) -> Path | None:
    """Return the single asset containing all three required frontend objects."""

    if not static_folder:
        return None
    try:
        static_root = Path(static_folder).resolve()
    except (OSError, TypeError, ValueError):
        return None

    with _LOCK:
        if static_root in _STATIC_FOLDER_ASSETS:
            return _STATIC_FOLDER_ASSETS[static_root]

        compatible: list[Path] = []
        for candidate in (static_root / "assets").glob("*.js"):
            try:
                source = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            transformed, status = transform_dashboard_javascript(source)
            if status == 1 and transformed != source:
                compatible.append(candidate.resolve())

        selected = compatible[0] if len(compatible) == 1 else None
        _STATIC_FOLDER_ASSETS[static_root] = selected
        return selected


def _adapt_static_asset(path: Path, *, compatible_asset: Path) -> Path:
    resolved = path.resolve()
    with _LOCK:
        if resolved != compatible_asset:
            return resolved
        cached = _CACHE.get(resolved)
        if cached is not None and cached.is_file():
            return cached
        if resolved in _MISSES or resolved.suffix.lower() != ".js":
            return resolved

        try:
            source = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _MISSES.add(resolved)
            return resolved

        transformed, status = transform_dashboard_javascript(source)
        if status != 1 or transformed == source:
            _MISSES.add(resolved)
            return resolved

        digest = hashlib.sha256(transformed.encode("utf-8")).hexdigest()[:16]
        target = _cache_root() / f"{resolved.stem}-{digest}{resolved.suffix}"
        target.write_text(transformed, encoding="utf-8", newline="")
        _CACHE[resolved] = target
        return target


def _adapt_index_file(path: Path, *, compatible_asset: Path) -> Path:
    resolved = path.resolve()
    with _LOCK:
        cached = _INDEX_CACHE.get(resolved)
        if cached is not None and cached.is_file():
            return cached

        transformed_asset = _adapt_static_asset(
            compatible_asset,
            compatible_asset=compatible_asset,
        )
        if transformed_asset.resolve() == compatible_asset.resolve():
            return resolved

        try:
            source = resolved.read_text(encoding="utf-8")
            transformed_bytes = transformed_asset.read_bytes()
        except (OSError, UnicodeError):
            return resolved

        asset_name = compatible_asset.name
        if asset_name not in source:
            return resolved

        digest = hashlib.sha256(transformed_bytes).hexdigest()[:16]
        replacement = f"{asset_name}?astrbot_volcengine={digest}"
        transformed_index = source.replace(asset_name, replacement)
        if transformed_index == source:
            return resolved

        target = _cache_root() / f"{resolved.stem}-{digest}{resolved.suffix}"
        target.write_text(transformed_index, encoding="utf-8", newline="")
        _INDEX_CACHE[resolved] = target
        return target


def acquire_dashboard_asset_bridge() -> bool:
    global _DASHBOARD_ASSET_LEASE_COUNT, _RESOLVE_WRAPPER, _RESOLVE_ORIGINAL
    global _INDEX_WRAPPER, _INDEX_ORIGINAL
    if _DASHBOARD_ASSET_LEASE_COUNT:
        _DASHBOARD_ASSET_LEASE_COUNT += 1
        return True

    try:
        from astrbot.dashboard.services import static_file_service

        StaticFileService = static_file_service.StaticFileService
    except (ImportError, ModuleNotFoundError):
        return False

    current = getattr(StaticFileService, "resolve_static_file", None)
    if getattr(current, "_volcengine_dashboard_asset_wrapper", False):
        current = getattr(current, "_volcengine_dashboard_asset_original", None)
    if not callable(current):
        return False

    index_current = getattr(StaticFileService, "resolve_index_file", None)
    if getattr(index_current, "_volcengine_dashboard_index_wrapper", False):
        index_current = getattr(index_current, "_volcengine_dashboard_index_original", None)

    def resolve_wrapper(
        self: Any,
        static_folder: str | Path | None,
        requested_path: str,
    ) -> Path | None:
        original_path = current(self, static_folder, requested_path)
        if not isinstance(original_path, Path):
            return original_path
        compatible_asset = _select_compatible_asset(static_folder)
        if compatible_asset is None:
            return original_path
        return _adapt_static_asset(original_path, compatible_asset=compatible_asset)

    resolve_wrapper._volcengine_dashboard_asset_wrapper = True  # type: ignore[attr-defined]
    resolve_wrapper._volcengine_dashboard_asset_original = current  # type: ignore[attr-defined]
    StaticFileService.resolve_static_file = resolve_wrapper  # type: ignore[method-assign]
    _RESOLVE_ORIGINAL, _RESOLVE_WRAPPER = current, resolve_wrapper

    if callable(index_current):

        def index_wrapper(
            self: Any,
            static_folder: str | Path | None,
        ) -> Path | None:
            original_path = index_current(self, static_folder)
            if not isinstance(original_path, Path):
                return original_path
            compatible_asset = _select_compatible_asset(static_folder)
            if compatible_asset is None:
                return original_path
            return _adapt_index_file(original_path, compatible_asset=compatible_asset)

        index_wrapper._volcengine_dashboard_index_wrapper = True  # type: ignore[attr-defined]
        index_wrapper._volcengine_dashboard_index_original = index_current  # type: ignore[attr-defined]
        StaticFileService.resolve_index_file = index_wrapper  # type: ignore[method-assign]
        _INDEX_ORIGINAL, _INDEX_WRAPPER = index_current, index_wrapper

    _DASHBOARD_ASSET_LEASE_COUNT = 1
    return True


def release_dashboard_asset_bridge() -> None:
    global _DASHBOARD_ASSET_LEASE_COUNT, _RESOLVE_WRAPPER, _RESOLVE_ORIGINAL
    global _INDEX_WRAPPER, _INDEX_ORIGINAL, _CACHE_ROOT

    if _DASHBOARD_ASSET_LEASE_COUNT <= 0:
        _DASHBOARD_ASSET_LEASE_COUNT = 0
        return
    _DASHBOARD_ASSET_LEASE_COUNT -= 1
    if _DASHBOARD_ASSET_LEASE_COUNT:
        return

    try:
        from astrbot.dashboard.services.static_file_service import StaticFileService
    except (ImportError, ModuleNotFoundError):
        StaticFileService = None  # type: ignore[assignment,misc]

    if StaticFileService is not None:
        if (
            _RESOLVE_WRAPPER is not None
            and getattr(StaticFileService, "resolve_static_file", None) is _RESOLVE_WRAPPER
            and _RESOLVE_ORIGINAL is not None
        ):
            StaticFileService.resolve_static_file = _RESOLVE_ORIGINAL  # type: ignore[method-assign]
        if (
            _INDEX_WRAPPER is not None
            and getattr(StaticFileService, "resolve_index_file", None) is _INDEX_WRAPPER
            and _INDEX_ORIGINAL is not None
        ):
            StaticFileService.resolve_index_file = _INDEX_ORIGINAL  # type: ignore[method-assign]

    with _LOCK:
        if _CACHE_ROOT is not None:
            shutil.rmtree(_CACHE_ROOT, ignore_errors=True)
        _CACHE_ROOT = None
        _CACHE.clear()
        _INDEX_CACHE.clear()
        _MISSES.clear()
        _STATIC_FOLDER_ASSETS.clear()
    _RESOLVE_ORIGINAL = _RESOLVE_WRAPPER = None
    _INDEX_ORIGINAL = _INDEX_WRAPPER = None
