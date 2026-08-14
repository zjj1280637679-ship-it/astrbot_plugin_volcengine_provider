"""Reversible Dashboard adaptation for source-scoped model-card fields.

AstrBot 4.27 builds every model dialog from one shared schema clone.  The
selected Provider Source type is available only in the Dashboard composable,
so a backend-only schema mutation cannot express "video for these two source
types" without leaking the option to every provider.

This bridge transforms the already-built provider-dialog JavaScript while it
is served.  The original AstrBot asset is never modified on disk.  A strict
single-match probe makes an unknown Dashboard build degrade to the backend
Video fallback instead of blocking the plugin or guessing at a new frontend
contract.  The served index is also copied with a content-derived query suffix
for the compatible bundle so an already-cached Dashboard must request the
current transformed asset after plugin install/update.
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
from .video_modality_fallback import VIDEO_MODALITY_FALLBACK_MARKER

_PATCH_MARKER = "/*astrbot-volcengine-model-dialog-v1*/"
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

# Current AstrBot emits this logic from useProviderModelConfigDialog.ts.  The
# expression is deliberately structural: minified variable names may change,
# while the Google-only hidden field and following schema-item loop identify
# the exact model-dialog clone boundary.
_MODEL_DIALOG_BOUNDARY = re.compile(
    r'(?P<source_type>[A-Za-z_$][\w$]*)==="googlegenai_chat_completion"'
    r'&&(?P<hidden>[A-Za-z_$][\w$]*)\.push\("custom_extra_body"\);'
    r'for\(const (?P<item>[A-Za-z_$][\w$]*) of (?P=hidden)\)'
    r'(?P<schema>[A-Za-z_$][\w$]*)\.provider\.items\[(?P=item)\]'
)


def _adaptation_javascript(*, source_type: str, schema: str) -> str:
    owned_types = json.dumps(sorted(OWNED_SOURCE_TYPES), ensure_ascii=False)
    plugin_fields = json.dumps(sorted(MODEL_FIELD_SCHEMA), ensure_ascii=False)
    fallback_marker = json.dumps(VIDEO_MODALITY_FALLBACK_MARKER, ensure_ascii=False)
    return (
        _PATCH_MARKER
        + f"const __abVolcModalities={schema}.provider.items.modalities;"
        + "const __abVolcLocale=globalThis.localStorage?.getItem?.(\"astrbot-locale\")||\"zh-CN\";"
        + "const __abVolcLabels5={"
        + "\"zh-CN\":[\"文本\",\"图像\",\"音频\",\"工具使用\",\"视频\"],"
        + "\"en-US\":[\"Text\",\"Image\",\"Audio\",\"Tool use\",\"Video\"],"
        + "\"ru-RU\":[\"Текст\",\"Изображение\",\"Аудио\",\"Инструменты\",\"Видео\"]};"
        + "const __abVolcLabels4={"
        + "\"zh-CN\":[\"文本\",\"图像\",\"音频\",\"工具使用\"],"
        + "\"en-US\":[\"Text\",\"Image\",\"Audio\",\"Tool use\"],"
        + "\"ru-RU\":[\"Текст\",\"Изображение\",\"Аудио\",\"Инструменты\"]};"
        + f"if({owned_types}.includes({source_type})){{"
        + "if(__abVolcModalities){"
        + f"let __abVolcFallback=__abVolcModalities[{fallback_marker}]===true;"
        + "const __abVolcOptions=Array.isArray(__abVolcModalities.options)"
        + "?__abVolcModalities.options:[];"
        + "if(!__abVolcOptions.includes(\"video\")){"
        + "__abVolcModalities.options=[...__abVolcOptions,\"video\"];"
        + "__abVolcFallback=true;"
        + "}"
        + "if(__abVolcFallback)"
        + "__abVolcModalities.labels=__abVolcLabels5[__abVolcLocale]||__abVolcLabels5[\"en-US\"];"
        + f"delete __abVolcModalities[{fallback_marker}];"
        + "}"
        + "}else{"
        + "if(__abVolcModalities"
        + f"&&__abVolcModalities[{fallback_marker}]===true){{"
        + "const __abVolcForeignOptions=Array.isArray(__abVolcModalities.options)"
        + "?__abVolcModalities.options:[];"
        + "__abVolcModalities.options=__abVolcForeignOptions.filter((__abVolcValue)=>__abVolcValue!==\"video\");"
        + "__abVolcModalities.labels=__abVolcLabels4[__abVolcLocale]||__abVolcLabels4[\"en-US\"];"
        + f"delete __abVolcModalities[{fallback_marker}];"
        + "}"
        + f"for(const __abVolcKey of {plugin_fields}){{"
        + f"const __abVolcField={schema}.provider.items[__abVolcKey];"
        + "if(__abVolcField)__abVolcField.invisible=true;"
        + "}"
        + "}"
    )


def transform_dashboard_javascript(source: str) -> tuple[str, int]:
    """Return the source-scoped model-dialog asset and structural match count."""

    if _PATCH_MARKER in source:
        return source, 1
    matches = list(_MODEL_DIALOG_BOUNDARY.finditer(source))
    if len(matches) != 1:
        return source, len(matches)

    match = matches[0]
    insertion = _adaptation_javascript(
        source_type=match.group("source_type"),
        schema=match.group("schema"),
    )
    offset = match.start() + match.group(0).index("for(")
    return source[:offset] + insertion + source[offset:], 1


def _cache_root() -> Path:
    global _CACHE_ROOT
    if _CACHE_ROOT is None:
        _CACHE_ROOT = Path(tempfile.mkdtemp(prefix="astrbot-volcengine-dashboard-"))
    return _CACHE_ROOT


def _select_compatible_asset(static_folder: str | Path | None) -> Path | None:
    """Resolve the one compatible asset from the Dashboard actually being served."""

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
            transformed, matches = transform_dashboard_javascript(source)
            if matches == 1 and transformed != source:
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

        transformed, matches = transform_dashboard_javascript(source)
        if matches != 1 or transformed == source:
            _MISSES.add(resolved)
            return resolved

        digest = hashlib.sha256(transformed.encode("utf-8")).hexdigest()[:16]
        target = _cache_root() / f"{resolved.stem}-{digest}{resolved.suffix}"
        target.write_text(transformed, encoding="utf-8", newline="")
        _CACHE[resolved] = target
        return target


def _adapt_index_file(path: Path, *, compatible_asset: Path) -> Path:
    """Return a copied index that forces one request for the transformed bundle."""

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
    """Install reversible static/index resolver wrappers when AstrBot has them."""

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
        return _adapt_static_asset(
            original_path,
            compatible_asset=compatible_asset,
        )

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
            return _adapt_index_file(
                original_path,
                compatible_asset=compatible_asset,
            )

        index_wrapper._volcengine_dashboard_index_wrapper = True  # type: ignore[attr-defined]
        index_wrapper._volcengine_dashboard_index_original = index_current  # type: ignore[attr-defined]
        StaticFileService.resolve_index_file = index_wrapper  # type: ignore[method-assign]
        _INDEX_ORIGINAL, _INDEX_WRAPPER = index_current, index_wrapper

    _DASHBOARD_ASSET_LEASE_COUNT = 1
    return True


def release_dashboard_asset_bridge() -> None:
    """Restore AstrBot resolvers and delete only this bridge's temporary copies."""

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
            and getattr(StaticFileService, "resolve_static_file", None)
            is _RESOLVE_WRAPPER
            and _RESOLVE_ORIGINAL is not None
        ):
            StaticFileService.resolve_static_file = _RESOLVE_ORIGINAL  # type: ignore[method-assign]
        if (
            _INDEX_WRAPPER is not None
            and getattr(StaticFileService, "resolve_index_file", None)
            is _INDEX_WRAPPER
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
