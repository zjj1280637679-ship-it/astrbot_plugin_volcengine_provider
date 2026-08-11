from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.core.agent.message import TextPart
from astrbot_plugin_volcengine_provider.adapters.errors import AdapterInputTransportError
from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    VIDEO_INPUT_ENABLED_KEY,
    cleanup_owned_settings_on_source_change,
    clear_source_model_hints,
    consume_source_model_hints,
    migrate_legacy_video_settings,
    normalize_owned_model_card_for_save,
    remember_source_model_hint,
    video_input_enabled,
)
from astrbot_plugin_volcengine_provider.metadata.agent_plan import KNOWN_AGENT_PLAN_MODELS
from astrbot_plugin_volcengine_provider.metadata.ark import normalize_ark_model_metadata
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk
from astrbot_plugin_volcengine_provider.registry import (
    _inject_model_card_video_control,
    _merge_source_feedback,
    _video_ui_key,
)


def main() -> None:
    assert video_input_enabled({}) is False
    assert video_input_enabled({VIDEO_INPUT_ENABLED_KEY: True}) is True
    assert video_input_enabled({'modalities': ['text', 'video']}) is False

    sources = [
        {'id': 'ark', 'type': ARK_PROVIDER_TYPE},
        {'id': 'foreign', 'type': 'openai_chat_completion'},
    ]
    card = {
        'id': 'ark/a',
        'provider_source_id': 'ark',
        'modalities': ['text', 'image'],
    }
    before = copy.deepcopy(card['modalities'])
    normalize_owned_model_card_for_save(card, sources, default_enabled=False)
    assert card[VIDEO_INPUT_ENABLED_KEY] is False
    assert card['modalities'] == before

    cfg = {
        'provider_sources': [
            {'id': 'ark', 'type': ARK_PROVIDER_TYPE, 'volcengine_ark_video_input': True},
            {'id': 'foreign', 'type': 'openai_chat_completion'},
        ],
        'provider': [
            {'id': 'ark/legacy', 'provider_source_id': 'ark', 'modalities': ['text', 'video']},
            {'id': 'foreign/m', 'provider_source_id': 'foreign', 'modalities': ['text', 'video']},
        ],
    }
    changed = migrate_legacy_video_settings(cfg)
    assert changed == ['ark/legacy']
    assert cfg['provider'][0][VIDEO_INPUT_ENABLED_KEY] is True
    assert cfg['provider'][0]['modalities'] == ['text', 'video']
    assert VIDEO_INPUT_ENABLED_KEY not in cfg['provider'][1]
    assert 'volcengine_ark_video_input' not in cfg['provider_sources'][0]

    # Legacy explicit Source=False must outrank an even older video modality.
    source_disabled = {
        'provider_sources': [
            {'id': 'ark', 'type': ARK_PROVIDER_TYPE, 'volcengine_ark_video_input': False},
        ],
        'provider': [
            {'id': 'ark/disabled', 'provider_source_id': 'ark', 'modalities': ['text', 'video']},
        ],
    }
    changed = migrate_legacy_video_settings(source_disabled)
    assert changed == ['ark/disabled']
    assert source_disabled['provider'][0][VIDEO_INPUT_ENABLED_KEY] is False
    assert source_disabled['provider'][0]['modalities'] == ['text', 'video']

    source_disabled_plan = {
        'provider_sources': [
            {
                'id': 'plan',
                'type': AGENT_PLAN_PROVIDER_TYPE,
                'volcengine_agent_plan_video_input': False,
            },
        ],
        'provider': [
            {'id': 'plan/disabled', 'provider_source_id': 'plan', 'modalities': ['text', 'video']},
        ],
    }
    changed = migrate_legacy_video_settings(source_disabled_plan)
    assert changed == ['plan/disabled']
    assert source_disabled_plan['provider'][0][VIDEO_INPUT_ENABLED_KEY] is False
    assert source_disabled_plan['provider'][0]['modalities'] == ['text', 'video']

    # A per-card legacy value remains newer/more specific than a Source value.
    per_card_override = {
        'provider_sources': [
            {'id': 'ark', 'type': ARK_PROVIDER_TYPE, 'volcengine_ark_video_input': False},
        ],
        'provider': [
            {
                'id': 'ark/override',
                'provider_source_id': 'ark',
                'volcengine_model_video_input': True,
                'modalities': ['text'],
            },
        ],
    }
    changed = migrate_legacy_video_settings(per_card_override)
    assert changed == ['ark/override']
    assert per_card_override['provider'][0][VIDEO_INPUT_ENABLED_KEY] is True
    assert per_card_override['provider'][0]['modalities'] == ['text']
    assert 'volcengine_model_video_input' not in per_card_override['provider'][0]

    # Source ownership cleanup can remove only plugin-owned configuration.
    changed_card = {
        'id': 'changed/card',
        'provider_source_id': 'ark',
        VIDEO_INPUT_ENABLED_KEY: True,
        'modalities': ['text', 'video'],
    }
    cleanup_owned_settings_on_source_change(
        changed_card,
        old_source_type=ARK_PROVIDER_TYPE,
        new_source_type='openai_chat_completion',
    )
    assert VIDEO_INPUT_ENABLED_KEY not in changed_card
    assert changed_card['modalities'] == ['text', 'video']

    # Explicit false/empty/0 are current feedback and must survive normalization.
    model_id, hint = normalize_ark_model_metadata({
        'id': 'm',
        'modalities': {'input_modalities': [], 'output_modalities': []},
        'token_limits': {'context_window': 0, 'max_output_token_length': 0},
        'features': {'tools': {'function_calling': False}, 'reasoning': False},
    })
    assert model_id == 'm'
    assert hint['modalities'] == {'input': [], 'output': []}
    assert hint['limit'] == {'context': 0, 'output': 0}
    assert hint['tool_call'] is False
    assert hint['reasoning'] is False

    # Unknown future modality tokens are information, not something today's
    # adapter vocabulary is authorized to erase.
    _, future = normalize_ark_model_metadata({
        'id': 'future',
        'modalities': {
            'input_modalities': ['text', 'future_sensor', 'future_sensor'],
            'output_modalities': ['future_stream'],
        },
    })
    assert future['modalities']['input'] == ['text', 'future_sensor']
    assert future['modalities']['output'] == ['future_stream']

    # Current receipt overlays explicit fields, but absence preserves host data.
    base = {
        'tool_call': True,
        'reasoning': True,
        'modalities': {'input': ['text', 'image'], 'output': ['text']},
        'limit': {'context': 131072, 'output': 8192},
    }
    merged = _merge_source_feedback(base, {
        'tool_call': False,
        'modalities': {'input': []},
        'limit': {'context': 0},
    })
    assert merged['tool_call'] is False
    assert merged['reasoning'] is True
    assert merged['modalities']['input'] == []
    assert merged['modalities']['output'] == ['text']
    assert merged['limit']['context'] == 0
    assert merged['limit']['output'] == 8192

    # Source feedback is a current-call mailbox, not reusable history.
    clear_source_model_hints('source')
    remember_source_model_hint('source', 'm', {'id': 'm', 'tool_call': False})
    first = consume_source_model_hints('source', ['m'])
    second = consume_source_model_hints('source', ['m'])
    assert first['m']['tool_call'] is False
    assert second == {}

    # ContextVar isolation prevents same-source concurrent model-list calls from
    # overwriting each other's current receipt.
    async def isolated_feedback(value: bool) -> bool:
        clear_source_model_hints('same-source')
        remember_source_model_hint(
            'same-source',
            'same-model',
            {'id': 'same-model', 'tool_call': value},
        )
        await asyncio.sleep(0)
        result = consume_source_model_hints('same-source', ['same-model'])
        return result['same-model']['tool_call']

    async def run_isolation() -> list[bool]:
        return list(await asyncio.gather(
            isolated_feedback(True),
            isolated_feedback(False),
        ))

    assert asyncio.run(run_isolation()) == [True, False]

    payload = {
        'config_schema': {'provider': {'items': {}}},
        'provider_sources': sources,
        'providers': [
            {'id': 'ark/a', 'provider_source_id': 'ark', 'model': 'same'},
            {'id': 'foreign/a', 'provider_source_id': 'foreign', 'model': 'same'},
        ],
    }
    out = _inject_model_card_video_control(payload)
    # The Dashboard projection must hide the canonical persistence key and expose
    # only the owned Source-scoped temporary UI value. Foreign cards get neither.
    assert VIDEO_INPUT_ENABLED_KEY not in out['providers'][0]
    assert out['providers'][0][_video_ui_key('ark')] is False
    assert VIDEO_INPUT_ENABLED_KEY not in out['providers'][1]
    assert _video_ui_key('ark') not in out['providers'][1]

    # Agent Plan list remains discovery-only and includes third parties.
    assert 'deepseek-v4-pro' in KNOWN_AGENT_PLAN_MODELS
    assert 'glm-5.2' in KNOWN_AGENT_PLAN_MODELS

    provider = ProviderVolcengineArk({
        'id': 'video-test',
        'provider': 'volcengine',
        'type': ARK_PROVIDER_TYPE,
        'provider_type': 'chat_completion',
        'enable': True,
        'key': ['dummy-key'],
        'api_base': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'dummy-model',
        VIDEO_INPUT_ENABLED_KEY: True,
    }, {'request_max_retries': 1})

    assert provider.provider_config[VIDEO_INPUT_ENABLED_KEY] is True

    # Local video resolution failures are provenance only and carry no routing advice.
    import astrbot_plugin_volcengine_provider.adapters.video as video_adapter
    original_resolver = video_adapter.resolve_video_reference

    async def fail_video(_: str) -> str:
        raise ValueError('synthetic local video failure')

    video_adapter.resolve_video_reference = fail_video
    try:
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': '[Video Attachment: name a.mp4, path dummy]'},
            ],
        }]
        parts = [TextPart(text='[Video Attachment: name a.mp4, path dummy]')]
        try:
            asyncio.run(video_adapter.inject_current_request_videos(messages, parts, enabled=True))
            raise AssertionError('expected AdapterInputTransportError')
        except AdapterInputTransportError as exc:
            assert exc.reached_model is False
            assert exc.capability_observed is None
            assert not hasattr(exc, 'fallback_recommended')
            assert exc.media_type == 'video'
    finally:
        video_adapter.resolve_video_reference = original_resolver

    # Audio normalization errors are wrapped with the same provenance contract.
    import astrbot_plugin_volcengine_provider.adapters.audio as audio_adapter
    original_audio_normalize = audio_adapter.normalize_ark_chat_audio

    async def fail_audio(_: str) -> bytes:
        raise ValueError('synthetic local audio failure')

    audio_adapter.normalize_ark_chat_audio = fail_audio
    try:
        try:
            asyncio.run(audio_adapter.build_ark_input_audio('dummy'))
            raise AssertionError('expected AdapterInputTransportError')
        except AdapterInputTransportError as exc:
            assert exc.reached_model is False
            assert exc.capability_observed is None
            assert not hasattr(exc, 'fallback_recommended')
            assert exc.media_type == 'audio'
            assert exc.stage == 'normalize_for_ark'
    finally:
        audio_adapter.normalize_ark_chat_audio = original_audio_normalize

    semantics = json.loads((ROOT / 'capabilities' / 'SEMANTICS.json').read_text('utf-8'))
    assert semantics['epistemic_contract']['feedback_is_truth'] is False
    assert semantics['epistemic_contract']['missing_feedback_means_unsupported'] is False
    assert semantics['live_model_feedback']['ordinary_ark_models_receipt']['persistent'] is False
    assert semantics['failure_domains']['input_transport']['reached_model'] is False
    assert semantics['failure_domains']['input_transport']['routing_advice'] is None
    assert semantics['future_extension_policy']['preserve_unknown_future_feedback_tokens'] is True
    assert semantics['fields'][VIDEO_INPUT_ENABLED_KEY]['kind'] == 'request_transport_switch'

    print('FEEDBACK_BOUNDARY_0_1_15=OK')


if __name__ == '__main__':
    main()
