"""Volcengine Ark provider plugin for AstrBot.

Importing a utility submodule must not register Provider types. AstrBot's plugin
entrypoint (``main.py``) explicitly imports ``providers`` for that lifecycle
side effect. Root-level Provider exports remain available lazily for backwards
compatibility with callers that intentionally request them.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "AGENT_PLAN_PREFIX",
    "AGENT_PLAN_PROVIDER_TYPE",
    "ARK_PROVIDER_TYPE",
    "ProviderVolcengineAgentPlan",
    "ProviderVolcengineArk",
    "VOLCENGINE_BRAND_KEY",
]

_PROVIDER_EXPORTS = frozenset(__all__)

if TYPE_CHECKING:
    from .providers import (
        AGENT_PLAN_PREFIX,
        AGENT_PLAN_PROVIDER_TYPE,
        ARK_PROVIDER_TYPE,
        ProviderVolcengineAgentPlan,
        ProviderVolcengineArk,
        VOLCENGINE_BRAND_KEY,
    )


def __getattr__(name: str) -> Any:
    """Load Provider-facing exports only when a caller explicitly requests one."""

    if name not in _PROVIDER_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    providers = import_module(f"{__name__}.providers")
    value = getattr(providers, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | _PROVIDER_EXPORTS)
