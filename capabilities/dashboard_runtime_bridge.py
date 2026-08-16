"""Inject a source-scoped runtime adapter into the served AstrBot Dashboard.

The compiled-asset transformer in :mod:`dashboard_asset_bridge` remains useful
when one exact AstrBot bundle exposes all three known structural boundaries, but
a real installation may serve a separately built Dashboard whose minified
identifier shape differs from the CI-built bundle even when both report the same
AstrBot version.  In that state the class-level static-file wrapper can be
installed successfully while no compatible JavaScript asset is selected, so an
"active" wrapper must not be treated as evidence that the concrete model-card
objects were adapted.

This bridge changes a different, more stable object: the already-created
``AstrBotConfig`` Vue component instance inside one visible model-card dialog.
After the component's concrete ``iterable.provider_source_id`` is available, the
bridge reads the current Provider Source mapping from AstrBot's authenticated
``/api/v1/providers/schema`` response and mutates only the private metadata and
reactive data object belonging to a card whose Source ``type`` is one of this
plugin's two registered types.  The native Video checkbox therefore remains an
ordinary AstrBot ``modalities`` v-model member and the lower request rows remain
ordinary ``AstrBotConfig`` members included in AstrBot's normal save payload;
foreign cards are never selected by endpoint, key, model ID, source ID prefix or
DOM position.

The original Dashboard index is never modified on disk.  Releasing the bridge
restores the host method and removes only plugin-owned temporary files; a page
that was already open naturally keeps its already-loaded script until the user
refreshes it, after which an uninstalled plugin leaves no public UI adaptation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import textwrap
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .model_fields import MODEL_FIELD_SCHEMA
from .model_scope import OWNED_SOURCE_TYPES

_RUNTIME_SCRIPT_ELEMENT_ID = "astrbot-volcengine-model-card-runtime-v1"
_RUNTIME_BRIDGE_VERSION = "0.1.24-real-device-v1"
_RUNTIME_BRIDGE_LEASE_COUNT = 0
_INDEX_WRAPPER: Callable[..., Any] | None = None
_INDEX_ORIGINAL: Callable[..., Any] | None = None
_CACHE_ROOT: Path | None = None
_INDEX_CACHE: dict[Path, Path] = {}
_LOCK = threading.RLock()

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


def _runtime_bridge_javascript() -> str:
    """Return one idempotent same-origin runtime adapter.

    The script never reads or serializes Provider keys.  Its authenticated schema
    request retains only Provider Source ``id`` and ``type`` so ownership remains
    the sole selection criterion.
    """

    owned_types = json.dumps(
        sorted(OWNED_SOURCE_TYPES),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    field_keys = json.dumps(
        list(MODEL_FIELD_SCHEMA),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    defaults = json.dumps(
        _NEW_CARD_DEFAULTS,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    version = json.dumps(_RUNTIME_BRIDGE_VERSION)

    return textwrap.dedent(
        f"""
        (() => {{
          "use strict";
          const BRIDGE_KEY = "__astrbotVolcengineModelCardRuntime";
          const VERSION = {version};
          if (globalThis[BRIDGE_KEY]?.version === VERSION) return;

          const OWNED_TYPES = new Set({owned_types});
          const FIELD_KEYS = {field_keys};
          const DEFAULTS = {defaults};
          const state = {{
            version: VERSION,
            indexScriptLoaded: true,
            sourceRefreshes: 0,
            dialogsObserved: 0,
            ownedDialogsCompleted: 0,
            lastSourceId: null,
            lastSourceType: null,
            lastError: null
          }};
          globalThis[BRIDGE_KEY] = state;

          const sourceTypes = new Map();
          const completedObjects = new WeakSet();
          let refreshPromise = null;
          let lastRefreshAt = 0;
          let scanTimer = 0;

          function cloneDefault(value) {{
            if (typeof structuredClone === "function") {{
              try {{ return structuredClone(value); }} catch (_) {{}}
            }}
            return JSON.parse(JSON.stringify(value));
          }}

          function videoLabel() {{
            const locale = String(
              localStorage.getItem("astrbot-locale") || navigator.language || "zh-CN"
            ).toLowerCase();
            if (locale.startsWith("zh")) return "视频";
            if (locale.startsWith("ru")) return "Видео";
            return "Video";
          }}

          async function refreshSourceTypes(force = false) {{
            const now = Date.now();
            if (!force && sourceTypes.size && now - lastRefreshAt < 3000) {{
              return sourceTypes;
            }}
            if (refreshPromise) return refreshPromise;

            refreshPromise = (async () => {{
              const headers = {{ Accept: "application/json" }};
              const token = localStorage.getItem("token");
              const locale = localStorage.getItem("astrbot-locale");
              if (token) headers.Authorization = `Bearer ${{token}}`;
              if (locale) headers["Accept-Language"] = locale;

              const response = await fetch("/api/v1/providers/schema", {{
                method: "GET",
                headers,
                credentials: "same-origin",
                cache: "no-store"
              }});
              if (!response.ok) {{
                throw new Error(`provider schema HTTP ${{response.status}}`);
              }}
              const body = await response.json();
              const data = body && typeof body === "object" && "data" in body
                ? body.data
                : body;
              const sources = Array.isArray(data?.provider_sources)
                ? data.provider_sources
                : [];

              sourceTypes.clear();
              for (const source of sources) {{
                const id = String(source?.id || "").trim();
                const type = String(source?.type || "").trim();
                if (id) sourceTypes.set(id, type);
              }}
              lastRefreshAt = Date.now();
              state.sourceRefreshes += 1;
              return sourceTypes;
            }})()
              .catch((error) => {{
                state.lastError = String(error?.message || error);
                return sourceTypes;
              }})
              .finally(() => {{
                refreshPromise = null;
              }});
            return refreshPromise;
          }}

          function isVisible(element) {{
            if (!(element instanceof Element)) return false;
            const style = getComputedStyle(element);
            return style.display !== "none"
              && style.visibility !== "hidden"
              && element.getClientRects().length > 0;
          }}

          function componentChain(element) {{
            const result = [];
            const seen = new Set();
            let instance = element?.__vueParentComponent || null;
            while (instance && !seen.has(instance)) {{
              seen.add(instance);
              result.push(instance);
              instance = instance.parent || null;
            }}
            return result;
          }}

          function findProviderConfigInstance(root) {{
            const nodes = [
              root,
              ...root.querySelectorAll(".object-config,.config-item,.w-100")
            ];
            for (const node of nodes) {{
              for (const instance of componentChain(node)) {{
                const props = instance?.props;
                const iterable = props?.iterable;
                const items = props?.metadata?.provider?.items;
                if (
                  props?.metadataKey === "provider"
                  && iterable
                  && items
                  && iterable.provider_source_id
                  && iterable.model
                ) {{
                  return instance;
                }}
              }}
            }}
            return null;
          }}

          function findModalitiesRenderer(root) {{
            const nodes = [
              ...root.querySelectorAll(".checkbox-group,.config-checkbox,.w-100")
            ];
            for (const node of nodes) {{
              for (const instance of componentChain(node)) {{
                if (
                  instance?.props?.configKey === "modalities"
                  && instance?.props?.itemMeta
                ) {{
                  return {{ instance, node }};
                }}
              }}
            }}
            return null;
          }}

          function translatedHostLabels(root, modalityMeta, optionCount) {{
            const renderer = findModalitiesRenderer(root);
            if (renderer) {{
              const resolver = renderer.instance?.setupState?.getTranslatedLabels;
              if (typeof resolver === "function") {{
                try {{
                  const resolved = resolver(modalityMeta);
                  if (Array.isArray(resolved) && resolved.length >= optionCount) {{
                    return resolved.slice(0, optionCount);
                  }}
                }} catch (_) {{}}
              }}

              const rendererRoot = renderer.instance?.subTree?.el;
              const queryRoot = rendererRoot instanceof Element
                ? rendererRoot
                : renderer.node.closest(".w-100") || root;
              const labels = [...queryRoot.querySelectorAll(".config-checkbox .v-label")]
                .map((element) => String(element.textContent || "").trim())
                .filter(Boolean);
              if (labels.length >= optionCount) return labels.slice(0, optionCount);
            }}

            if (Array.isArray(modalityMeta?.labels)
                && modalityMeta.labels.length >= optionCount) {{
              return modalityMeta.labels.slice(0, optionCount);
            }}
            return null;
          }}

          async function adaptDialog(root) {{
            const configInstance = findProviderConfigInstance(root);
            if (!configInstance) return false;

            const iterable = configInstance.props.iterable;
            const items = configInstance.props.metadata?.provider?.items;
            if (!items) return false;

            const sourceId = String(iterable.provider_source_id || "").trim();
            let sourceType = sourceTypes.get(sourceId) || "";
            if (!sourceType) {{
              await refreshSourceTypes(true);
              sourceType = sourceTypes.get(sourceId) || "";
            }}

            state.lastSourceId = sourceId;
            state.lastSourceType = sourceType;
            if (!OWNED_TYPES.has(sourceType)) return false;

            for (const key of FIELD_KEYS) {{
              const metadata = items[key];
              if (metadata) metadata.invisible = false;
              if (!(key in iterable)) iterable[key] = cloneDefault(DEFAULTS[key]);
            }}

            const modalityMeta = items.modalities;
            if (!modalityMeta || !Array.isArray(modalityMeta.options)) return false;

            if (!modalityMeta.options.includes("video")) {{
              const hostLabels = translatedHostLabels(
                root,
                modalityMeta,
                modalityMeta.options.length
              );
              if (!hostLabels && typeof modalityMeta.labels === "string") {{
                return false;
              }}
              modalityMeta.options.push("video");
              if (hostLabels) {{
                modalityMeta.labels = [...hostLabels, videoLabel()];
              }} else if (Array.isArray(modalityMeta.labels)) {{
                modalityMeta.labels = [...modalityMeta.labels, videoLabel()];
              }}
            }}

            const complete = modalityMeta.options.includes("video")
              && FIELD_KEYS.every((key) => key in iterable)
              && FIELD_KEYS.every((key) => !items[key] || items[key].invisible === false);
            if (complete && !completedObjects.has(iterable)) {{
              completedObjects.add(iterable);
              state.ownedDialogsCompleted += 1;
            }}
            return complete;
          }}

          async function scan() {{
            scanTimer = 0;
            const roots = [
              ...document.querySelectorAll(
                ".v-overlay.v-overlay--active,[role=dialog]"
              )
            ].filter(isVisible);
            state.dialogsObserved = roots.length;
            for (const root of roots) {{
              try {{
                const complete = await adaptDialog(root);
                if (!complete) scheduleScan(120);
              }} catch (error) {{
                state.lastError = String(error?.message || error);
              }}
            }}
          }}

          function scheduleScan(delay = 40) {{
            if (scanTimer) clearTimeout(scanTimer);
            scanTimer = setTimeout(scan, delay);
          }}

          const observer = new MutationObserver(() => scheduleScan());
          observer.observe(document.documentElement, {{
            childList: true,
            subtree: true
          }});
          window.addEventListener("hashchange", () => {{
            refreshSourceTypes(true).finally(() => scheduleScan());
          }});
          document.addEventListener("visibilitychange", () => {{
            if (!document.hidden) scheduleScan();
          }});

          refreshSourceTypes(true).finally(() => scheduleScan());
        }})();
        """
    ).strip()


def _cache_root() -> Path:
    global _CACHE_ROOT
    if _CACHE_ROOT is None:
        _CACHE_ROOT = Path(tempfile.mkdtemp(prefix="astrbot-volcengine-runtime-"))
    return _CACHE_ROOT


def _inject_runtime_bridge(path: Path) -> Path:
    resolved = path.resolve()
    with _LOCK:
        cached = _INDEX_CACHE.get(resolved)
        if cached is not None and cached.is_file():
            return cached

        try:
            source = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return resolved

        element_marker = f'id="{_RUNTIME_SCRIPT_ELEMENT_ID}"'
        if element_marker in source:
            return resolved

        script = _runtime_bridge_javascript()
        tag = f'<script id="{_RUNTIME_SCRIPT_ELEMENT_ID}">{script}</script>'
        if "</body>" in source:
            transformed = source.replace("</body>", f"{tag}</body>", 1)
        elif "</head>" in source:
            transformed = source.replace("</head>", f"{tag}</head>", 1)
        else:
            transformed = f"{source}\n{tag}\n"

        digest = hashlib.sha256(transformed.encode("utf-8")).hexdigest()[:16]
        target = _cache_root() / f"{resolved.stem}-{digest}{resolved.suffix}"
        target.write_text(transformed, encoding="utf-8", newline="")
        _INDEX_CACHE[resolved] = target
        return target


def acquire_dashboard_runtime_bridge() -> bool:
    """Wrap only the Dashboard index resolver and inject the runtime adapter."""

    global _RUNTIME_BRIDGE_LEASE_COUNT, _INDEX_WRAPPER, _INDEX_ORIGINAL
    if _RUNTIME_BRIDGE_LEASE_COUNT:
        _RUNTIME_BRIDGE_LEASE_COUNT += 1
        return True

    try:
        from astrbot.dashboard.services.static_file_service import StaticFileService
    except (ImportError, ModuleNotFoundError):
        return False

    current = getattr(StaticFileService, "resolve_index_file", None)
    if getattr(current, "_volcengine_dashboard_runtime_wrapper", False):
        current = getattr(current, "_volcengine_dashboard_runtime_original", None)
    if not callable(current):
        return False

    def index_wrapper(
        self: Any,
        static_folder: str | Path | None,
    ) -> Path | None:
        original_path = current(self, static_folder)
        if isinstance(original_path, Path):
            return _inject_runtime_bridge(original_path)
        if isinstance(original_path, str):
            return _inject_runtime_bridge(Path(original_path))
        return original_path

    index_wrapper._volcengine_dashboard_runtime_wrapper = True  # type: ignore[attr-defined]
    index_wrapper._volcengine_dashboard_runtime_original = current  # type: ignore[attr-defined]
    StaticFileService.resolve_index_file = index_wrapper  # type: ignore[method-assign]
    _INDEX_ORIGINAL, _INDEX_WRAPPER = current, index_wrapper
    _RUNTIME_BRIDGE_LEASE_COUNT = 1
    return True


def release_dashboard_runtime_bridge() -> None:
    """Release one lease and restore the host index resolver."""

    global _RUNTIME_BRIDGE_LEASE_COUNT, _INDEX_WRAPPER, _INDEX_ORIGINAL
    global _CACHE_ROOT

    if _RUNTIME_BRIDGE_LEASE_COUNT <= 0:
        _RUNTIME_BRIDGE_LEASE_COUNT = 0
        return
    _RUNTIME_BRIDGE_LEASE_COUNT -= 1
    if _RUNTIME_BRIDGE_LEASE_COUNT:
        return

    try:
        from astrbot.dashboard.services.static_file_service import StaticFileService
    except (ImportError, ModuleNotFoundError):
        StaticFileService = None  # type: ignore[assignment,misc]

    if (
        StaticFileService is not None
        and _INDEX_WRAPPER is not None
        and getattr(StaticFileService, "resolve_index_file", None) is _INDEX_WRAPPER
        and _INDEX_ORIGINAL is not None
    ):
        StaticFileService.resolve_index_file = _INDEX_ORIGINAL  # type: ignore[method-assign]

    with _LOCK:
        if _CACHE_ROOT is not None:
            shutil.rmtree(_CACHE_ROOT, ignore_errors=True)
        _CACHE_ROOT = None
        _INDEX_CACHE.clear()
    _INDEX_ORIGINAL = _INDEX_WRAPPER = None
