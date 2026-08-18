"""0.1.31 pre-feedback/post-feedback context governance contracts.

The tests deliberately use model names that *look* meaningful but never allow the
name itself to influence the result. Capability decisions must come from explicit
feedback and must have a bounded lifecycle.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot_plugin_volcengine_provider.capabilities import (
    ContextFeedbackLoop,
    context_guard_from_feedback,
    extract_reported_context_limit,
    requested_output_reserve,
)
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk


class FeedbackError(Exception):
    def __init__(self, message: str, *, body=None) -> None:
        super().__init__(message)
        self.body = body


def test_model_name_is_not_context_evidence() -> None:
    for model in (
        "deepseek-v4-flash-ga-260731",
        "glm-5.2",
        "doubao-seed-2.1-pro",
        "agentplan/ark-code-latest",
        "ep-dynamic-routing-alias",
    ):
        config = {"id": f"card/{model}", "model": model}
        loop = ContextFeedbackLoop(config)
        before = dict(config)
        snapshot = loop.pre_request(config, provider_id=config["id"])
        assert snapshot.guard is None
        assert snapshot.source == "unreported"
        assert config == before


def test_explicit_pre_feedback_is_used_without_name_inference() -> None:
    config = {
        "id": "card/a",
        "model": "totally-unknown-alias",
        "max_context_tokens": 262_144,
    }
    loop = ContextFeedbackLoop(config)
    snapshot = loop.pre_request(config, provider_id="card/a")
    assert snapshot.guard == 262_144
    assert snapshot.source == "pre_feedback"


def test_host_can_supply_late_pre_feedback_before_first_request() -> None:
    config = {"id": "card/a", "model": "unknown"}
    loop = ContextFeedbackLoop(config)
    config["max_context_tokens"] = 128_000
    snapshot = loop.pre_request(config, provider_id="card/a")
    assert snapshot.guard == 128_000
    assert snapshot.source == "pre_feedback"


def test_success_feedback_is_only_a_lower_bound() -> None:
    config = {"id": "card/a", "max_context_tokens": 128_000}
    loop = ContextFeedbackLoop(config)
    loop.pre_request(config, provider_id="card/a")
    snapshot = loop.post_success(
        prompt_tokens=120_000,
        completion_tokens=2_000,
        provider_id="card/a",
    )
    assert snapshot.accepted_input_high_water == 120_000
    assert snapshot.accepted_total_high_water == 122_000
    assert snapshot.guard == 128_000
    assert config["max_context_tokens"] == 128_000


def test_structured_post_feedback_can_raise_stale_host_fallback() -> None:
    config = {
        "id": "card/a",
        "model": "agentplan/ark-code-latest",
        "max_context_tokens": 128_000,
    }
    loop = ContextFeedbackLoop(config)
    loop.pre_request(config, provider_id="card/a")
    error = FeedbackError(
        "request rejected",
        body={
            "error": {
                "code": "context_length_exceeded",
                "details": {"maximum_context_length": 1_048_576},
            }
        },
    )
    snapshot = loop.post_context_rejection(
        config,
        error,
        {"max_tokens": 8_192},
        provider_id="card/a",
    )
    assert snapshot.reported_context_limit == 1_048_576
    assert snapshot.output_reserve == 8_192
    assert snapshot.guard == 1_040_384
    assert snapshot.source == "post_feedback"
    assert config["max_context_tokens"] == 1_040_384

    next_snapshot = loop.pre_request(config, provider_id="card/a")
    assert next_snapshot.guard == 1_040_384
    assert next_snapshot.source == "post_feedback"


def test_textual_post_feedback_can_lower_an_overlarge_guard() -> None:
    config = {"id": "card/a", "max_context_tokens": 1_000_000}
    loop = ContextFeedbackLoop(config)
    error = FeedbackError("Maximum context length is 262,144 tokens")
    snapshot = loop.post_context_rejection(
        config,
        error,
        {"max_completion_tokens": 4_096},
        provider_id="card/a",
    )
    assert snapshot.reported_context_limit == 262_144
    assert snapshot.guard == 258_048
    assert config["max_context_tokens"] == 258_048


def test_context_error_without_explicit_ceiling_cannot_mutate_guard() -> None:
    config = {
        "id": "card/a",
        "model": "deepseek-v4-pro",
        "max_context_tokens": 128_000,
    }
    loop = ContextFeedbackLoop(config)
    error = FeedbackError(
        "context length exceeded: requested 999999 tokens",
        body={"error": {"code": "context_length_exceeded"}},
    )
    snapshot = loop.post_context_rejection(
        config,
        error,
        {"max_tokens": 8_192},
        provider_id="card/a",
    )
    assert snapshot.reported_context_limit is None
    assert snapshot.guard == 128_000
    assert snapshot.source == "pre_feedback"
    assert config["max_context_tokens"] == 128_000


def test_unrelated_numeric_fields_are_not_context_feedback() -> None:
    error = FeedbackError(
        "bad request 400; requested 900000 tokens",
        body={
            "error": {
                "code": 400,
                "requested_tokens": 900_000,
                "max_output_tokens": 32_768,
            }
        },
    )
    assert extract_reported_context_limit(error) is None


def test_multiple_explicit_feedback_values_fail_conservatively() -> None:
    error = FeedbackError(
        "maximum context length is 524288 tokens",
        body={"error": {"max_context_tokens": 262_144}},
    )
    assert extract_reported_context_limit(error) == 262_144


def test_output_reserve_uses_all_explicit_request_feedback() -> None:
    assert requested_output_reserve({}) == 0
    assert requested_output_reserve({"max_tokens": 8_192}) == 8_192
    assert (
        requested_output_reserve(
            {
                "max_tokens": 4_096,
                "extra_body": {"max_completion_tokens": 16_384},
            }
        )
        == 16_384
    )
    assert (
        requested_output_reserve(
            {},
            {
                "custom_extra_body": {"max_tokens": 8_192},
                "volcengine_max_output_tokens": 32_768,
            },
        )
        == 32_768
    )
    assert context_guard_from_feedback(262_144, output_reserve=16_384) == 245_760
    assert context_guard_from_feedback(8_192, output_reserve=8_192) is None


def test_provider_rebuild_discards_runtime_post_feedback() -> None:
    persisted_pre_feedback = {
        "id": "card/a",
        "model": "agentplan/ark-code-latest",
        "max_context_tokens": 128_000,
    }
    live_config = dict(persisted_pre_feedback)
    first_lifecycle = ContextFeedbackLoop(live_config)
    first_lifecycle.post_context_rejection(
        live_config,
        FeedbackError("maximum context window is 1048576 tokens"),
        {"max_tokens": 8_192},
        provider_id="card/a",
    )
    assert live_config["max_context_tokens"] == 1_040_384

    rebuilt_config = dict(persisted_pre_feedback)
    second_lifecycle = ContextFeedbackLoop(rebuilt_config)
    snapshot = second_lifecycle.pre_request(rebuilt_config, provider_id="card/a")
    assert snapshot.guard == 128_000
    assert snapshot.source == "pre_feedback"


def test_same_alias_can_be_revised_by_new_feedback_not_by_its_name() -> None:
    config = {
        "id": "card/alias",
        "model": "agentplan/ark-code-latest",
        "max_context_tokens": 128_000,
    }
    loop = ContextFeedbackLoop(config)

    first = loop.post_context_rejection(
        config,
        FeedbackError("maximum context length is 1048576 tokens"),
        {"max_tokens": 8_192},
        provider_id="card/alias",
    )
    assert first.guard == 1_040_384

    second = loop.post_context_rejection(
        config,
        FeedbackError("maximum context length is 262144 tokens"),
        {"max_tokens": 8_192},
        provider_id="card/alias",
    )
    assert second.guard == 253_952
    assert config["model"] == "agentplan/ark-code-latest"


async def test_provider_error_hook_feeds_next_request_guard() -> None:
    provider = object.__new__(ProviderVolcengineArk)
    provider.provider_config = {
        "id": "ark/card",
        "model": "alias-without-capability-semantics",
        "max_context_tokens": 128_000,
        "volcengine_max_output_tokens": 8_192,
    }
    provider._context_feedback = ContextFeedbackLoop(provider.provider_config)

    original = ProviderOpenAIOfficial._handle_api_error

    async def fake_parent(*args, **kwargs):
        return (0, "chosen-key", [], 0, False)

    ProviderOpenAIOfficial._handle_api_error = fake_parent
    try:
        await provider._handle_api_error(
            FeedbackError("maximum context length is 1048576 tokens"),
            {"model": "alias-without-capability-semantics"},
            [],
            None,
            "chosen-key",
            [],
            0,
            2,
        )
    finally:
        ProviderOpenAIOfficial._handle_api_error = original

    assert provider.provider_config["max_context_tokens"] == 1_040_384
    next_pre = provider._context_feedback.pre_request(
        provider.provider_config,
        provider_id="ark/card",
    )
    assert next_pre.source == "post_feedback"
    assert next_pre.guard == 1_040_384


async def test_provider_success_hook_records_lower_bound_once() -> None:
    provider = object.__new__(ProviderVolcengineArk)
    provider.provider_config = {
        "id": "ark/card",
        "model": "alias",
        "max_context_tokens": 128_000,
    }
    provider._context_feedback = ContextFeedbackLoop(provider.provider_config)

    original = ProviderOpenAIOfficial._parse_openai_completion

    async def fake_parent(*args, **kwargs):
        return SimpleNamespace(role="assistant")

    ProviderOpenAIOfficial._parse_openai_completion = fake_parent
    try:
        completion = SimpleNamespace(
            model="resolved-label-only",
            usage=SimpleNamespace(
                prompt_tokens=100_000,
                completion_tokens=2_000,
                prompt_tokens_details=SimpleNamespace(cached_tokens=50_000),
                completion_tokens_details=SimpleNamespace(reasoning_tokens=500),
            ),
        )
        await provider._parse_openai_completion(completion, None)
    finally:
        ProviderOpenAIOfficial._parse_openai_completion = original

    snapshot = provider._context_feedback.pre_request(
        provider.provider_config,
        provider_id="ark/card",
    )
    assert snapshot.accepted_input_high_water == 100_000
    assert snapshot.accepted_total_high_water == 102_000
    assert snapshot.guard == 128_000


def test_stream_path_relies_on_final_parser_for_post_success() -> None:
    source = (
        ROOT
        / "AstrBot"
        / "data"
        / "plugins"
        / "astrbot_plugin_volcengine_provider"
        / "providers.py"
    ).read_text("utf-8")
    assert source.count("self._context_feedback.post_success(") == 1
    assert "parent stream creates a final ChatCompletion" in source


def main() -> None:
    test_model_name_is_not_context_evidence()
    test_explicit_pre_feedback_is_used_without_name_inference()
    test_host_can_supply_late_pre_feedback_before_first_request()
    test_success_feedback_is_only_a_lower_bound()
    test_structured_post_feedback_can_raise_stale_host_fallback()
    test_textual_post_feedback_can_lower_an_overlarge_guard()
    test_context_error_without_explicit_ceiling_cannot_mutate_guard()
    test_unrelated_numeric_fields_are_not_context_feedback()
    test_multiple_explicit_feedback_values_fail_conservatively()
    test_output_reserve_uses_all_explicit_request_feedback()
    test_provider_rebuild_discards_runtime_post_feedback()
    test_same_alias_can_be_revised_by_new_feedback_not_by_its_name()
    asyncio.run(test_provider_error_hook_feeds_next_request_guard())
    asyncio.run(test_provider_success_hook_records_lower_bound_once())
    test_stream_path_relies_on_final_parser_for_post_success()
    print("CONTEXT_FEEDBACK_LOOP_0_1_31=OK")


if __name__ == "__main__":
    main()
