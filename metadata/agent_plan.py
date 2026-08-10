"""Documented Agent Plan model facts cached for the inference plane.

The Agent Plan inference key has no documented OpenAI-style /models capability
receipt. Facts live here separately from Provider control flow so provenance
and staleness remain visible.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .common import _publish_metadata

AGENT_PLAN_FACTS_VERIFIED_AT = "2026-08-09"
AGENT_PLAN_FACTS_SOURCE_KIND = "Volcengine public package/model tables + live Agent Plan console"

# Agent Plan's inference-key plane has no documented /models route. Keep only
# active language models shown by the official Agent Plan console on
# 2026-08-09; users can still type a newer official model name manually.
# Models marked "即将下线" are deliberately omitted.
KNOWN_AGENT_PLAN_MODELS = (
    "doubao-seed-2.1-turbo",
    "doubao-seed-evolving",
    "doubao-seed-2.0-lite",
    "doubao-seed-2.0-mini",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "glm-latest",
    "kimi-k3",
    "kimi-k2.7-code",
    "minimax-m3",
    "ark-code-latest",
)

# The Plan control plane exposes only ModelID values. These limits and input
# modalities therefore follow the public package/model tables and the live
# console, rather than pretending the inference key returns a capability map.
# k-values in the public table are binary token units except the official
# ark-code-latest client example, which uses literal 256000/32000 limits.
AGENT_PLAN_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "doubao-seed-2.0-mini": {
        "input": ["text", "image", "video", "audio"],
        "context": 262_144,
        "output": 131_072,
    },
    "doubao-seed-2.0-lite": {
        "input": ["text", "image", "video", "audio"],
        "context": 262_144,
        "output": 131_072,
    },
    "deepseek-v4-flash": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 393_216,
    },
    "doubao-seed-2.1-turbo": {
        "input": ["text", "image", "video"],
        "context": 262_144,
        "output": 262_144,
    },
    "doubao-seed-evolving": {
        "input": ["text", "image", "video"],
        "context": 1_048_576,
        "output": 262_144,
    },
    "minimax-m3": {
        "input": ["text", "image"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "glm-5.2": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "glm-latest": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "kimi-k2.7-code": {
        "input": ["text", "image", "video"],
        "context": 262_144,
        "output": 32_768,
    },
    "deepseek-v4-pro": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 393_216,
    },
    "kimi-k3": {
        "input": ["text", "image"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "ark-code-latest": {
        "input": ["text", "image"],
        "context": 256_000,
        "output": 32_000,
    },
}


def publish_agent_plan_metadata(
    to_public_model: Callable[[object], str],
) -> None:
    """Publish the documented Plan fact snapshot under Provider-owned public IDs."""

    for upstream_id, spec in AGENT_PLAN_MODEL_SPECS.items():
        public_id = to_public_model(upstream_id)
        _publish_metadata(
            public_id,
            {
                "reasoning": spec.get("reasoning", True),
                "tool_call": spec.get("tool_call", True),
                "modalities": {
                    "input": list(spec["input"]),
                    "output": ["text"],
                },
                "limit": {
                    "context": int(spec["context"]),
                    "output": int(spec["output"]),
                },
            },
        )

