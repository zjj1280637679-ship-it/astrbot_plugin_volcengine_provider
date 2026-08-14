"""Reversible Dashboard adaptation for source-scoped model-card fields.

AstrBot 4.27 has two distinct frontend objects that this plugin must adapt without
collapsing their meanings:

* ``providerModelConfigSchema`` is a private metadata clone created only after the
  currently selected Provider Source type is known.  For Ark / Agent Plan model
  cards, that clone may gain one native ``video`` modality and may reveal the
  lower Volcengine-owned bilingual request-row metadata.  Foreign clones must keep
  AstrBot's native modalities untouched and those plugin rows hidden.
* ``buildModelProviderConfig(modelName)`` creates the concrete data object used as
  ``AstrBotConfig.iterable`` for a newly added model card.  AstrBot renders only
  keys that already exist on that concrete object, so an owned new card must also
  receive the lower Volcengine request-field default values there; foreign new
  cards must not receive those keys at all.

Both structural boundaries must occur exactly once in the same served Dashboard
asset before any transformation is accepted.  This prevents a partial patch in
which the upper capability row changes but the lower concrete data object does
not, or vice versa.  The original AstrBot asset is never modified on disk, and a
content-derived query suffix forces compatible browsers to request the current
transformed copy after install/update.
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

_PATCH_MARKER = "/*astrbot-volcengine-model-dialog-v3*/"
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
    # AstrBot 4.27.3 may return the concrete new-card object directly as
    # ``return {..}``, or through a comma expression that first derives another
    # host value and then returns that same concrete object as
    # ``return(<brace/semicolon-free prelude>, {..})``.  The optional prelude is
    # deliberately narrow so this matcher cannot jump into a later object literal.
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
    owned_types = json.dumps(sorted(OWNED_SOURCE_TYPES), ensure_ascii=False)
    plugin_fields = json.dumps(sorted(MODEL_FIELD_SCHEMA), ensure_ascii=False)
    localized_modalities = json.dumps(
        {
            "zh": ["文本", "图像", "音频", "工具使用", "视频"],
            "en": ["Text", "Image", "Audio", "Tool use", "Video"],
            "ru": ["Текст", "Изображение", "Аудио", "Инструменты", "Видео"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
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
        + "const __abVolcLang=(document.documentElement.lang||"
        + "globalThis.localStorage?.getItem?.(\"astrbot-locale\")||\"zh-CN\").toLowerCase();"
        + "const __abVolcLocale=__abVolcLang.startsWith(\"zh\")?\"zh\":"
        + "(__abVolcLang.startsWith(\"ru\")?\"ru\":\"en\");"
        + f"const __abVolcLocalizedModalities={localized_modalities};"
        + "if(Array.isArray(__abVolcModalities.labels)"
        + "&&__abVolcModalities.labels.length===__abVolcOptions.length){"
        + "__abVolcModalities.labels=[...__abVolcModalities.labels,"
        + "__abVolcLocalizedModalities[__abVolcLocale][4]];"
        + "}else if(typeof __abVolcModalities.labels===\"string\"){"
        + "__abVolcModalities.labels=[...__abVolcLocalizedModalities[__abVolcLocale]];"
        + "}"
        + "}"
        + "}else{"
        + "for(const __abVolcKey of __abVolcPluginFields){"
        + f"const __abVolcField={schema}.provider.items[__abVolcKey];"
        + "if(__abVolcField)__abVolcField.invisible=true;"
        + "}"
        + "}"
    )


def _builder_object_insertion(*, selected_source_ref: str) -> str:
    owned_types = json.dumps(sorted(OWNED_SOURCE_TYPES), ensure_ascii=False)
    defaults = json.dumps(_NEW_CARD_DEFAULTS, ensure_ascii=False, separators=(",", ":"))
    return (
        ",...(("
        + f"{selected_source_ref}.value"
        + ")&&"
        + f"{owned_types}.includes({selected_source_ref}.value.type)"
        + f"?{defaults}:{{}})"
    )


def transform_dashboard_javascript(source: str) -> tuple[str, int]:
    """Return status 1 only for a complete two-boundary compatible asset.

    The integer is a compatibility status, not a raw count: ``1`` means both
    concrete-object boundaries are uniquely known; ``0`` means at least one is
    absent while neither is ambiguous; ``>=2`` means at least one boundary is
    ambiguous.  This keeps a half-match from being mistaken for full support.
    """

    if _PATCH_MARKER in source:
        return source, 1

    dialog_matches = list(_MODEL_DIALOG_BOUNDARY.finditer(source))
    builder_matches = list(_MODEL_BUILDER_BOUNDARY.finditer(source))
    if len(dialog_matches) != 1 or len(builder_matches) != 1:
        if len(dialog_matches) <= 1 and len(builder_matches) <= 1:
            return source, 0
        return source, max(2, len(dialog_matches) + len(builder_matches))

    dialog = dialog_matches[0]
    builder = builder_matches[0]
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

    edits = sorted(
        ((dialog_offset, dialog_insertion), (builder_offset, builder_insertion)),
        key=lambda item: item[0],
        reverse=True,
    )
    transformed = source
    for offset, insertion in edits:
        transformed = transformed[:offset] + insertion + transformed[offset:]
    return transformed, 1


def _cache_root() -> Path:
    global _CACHE_ROOT
    if _CACHE_ROOT is None:
        _CACHE_ROOT = Path(tempfile.mkdtemp(prefix="astrbot-volcengine-dashboard-"))
    return _CACHE_ROOT


def _select_compatible_asset(static_folder: str | Path | None) -> Path | None:
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
