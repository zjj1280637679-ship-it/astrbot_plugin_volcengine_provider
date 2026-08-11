from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.core.agent.message import TextPart
from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    VIDEO_INPUT_ENABLED_KEY,
    cleanup_owned_settings_on_source_change,
    migrate_legacy_video_settings,
    normalize_owned_model_card_for_save,
    video_input_enabled,
)
from astrbot_plugin_volcengine_provider.metadata.agent_plan import KNOWN_AGENT_PLAN_MODELS
from astrbot_plugin_volcengine_provider.metadata.ark import normalize_ark_model_metadata
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk
from astrbot_plugin_volcengine_provider.registry import (
    _inject_model_card_video_control,
    _merge_source_feedback,
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
            {'id': 'foreign/a', 'provider_source_id': 'foreign', 'modalities': ['text']},
        ],
    }
    migrate_legacy_video_settings(cfg)
    assert cfg['provider'][0][VIDEO_INPUT_ENABLED_KEY] is True
    assert cfg['provider'][0]['modalities'] == ['text', 'video']
    assert VIDEO_INPUT_ENABLED_KEY not in cfg['provider'][1]
    assert 'volcengine_ark_video_input' not in cfg['provider_sources'][0]

    # Migration precedence is user-state preservation, not a capability guess:
    # new per-card > old per-card > explicit Source bool > modalities clue.
    precedence_cfg = {
        'provider_sources': [
            {
                'id': 'ark-off',
                'type': ARK_PROVIDER_TYPE,
                'volcengine_ark_video_input': False,
            },
            {
                'id': 'ark-on',
                'type': ARK_PROVIDER_TYPE,
                'volcengine_ark_video_input': True,
            },
            {
                'id': 'plan-off',
                'type': AGENT_PLAN_PROVIDER_TYPE,
                'volcengine_agent_plan_video_input': False,
            },
        ],
        'provider': [
            {
                'id': 'ark/source-disabled',
                'provider_source_id': 'ark-off',
                'modalities': ['text', 'video'],
            },
            {
                'id': 'ark/model-override',
                'provider_source_id': 'ark-off',
                'volcengine_model_video_input': True,
                'modalities': ['text', 'video'],
            },
            {
                'id': 'ark/new-override',
                'provider_source_id': 'ark-on',
                VIDEO_INPUT_ENABLED_KEY: False,
                'modalities': ['text', 'video'],
            },
            {
                'id': 'plan/source-disabled',
                'provider_source_id': 'plan-off',
                'modalities': ['text', 'video'],
            },
        ],
    }
    migrate_legacy_video_settings(precedence_cfg)
    cards = {card['id']: card for card in precedence_cfg['provider']}
    assert cards['ark/source-disabled'][VIDEO_INPUT_ENABLED_KEY] is False
    assert cards['ark/source-disabled']['modalities'] == ['text', 'video']
    assert cards['ark/model-override'][VIDEO_INPUT_ENABLED_KEY] is True
    assert 'volcengine_model_video_input' not in cards['ark/model-override']
    assert cards['ark/new-override'][VIDEO_INPUT_ENABLED_KEY] is False
    assert cards['plan/source-disabled'][VIDEO_INPUT_ENABLED_KEY] is False
    assert all(
        'volcengine_ark_video_input' not in source
        and 'volcengine_agent_plan_video_input' not in source
        for source in precedence_cfg['provider_sources']
    )

    moving = {
        'provider_source_id': 'foreign',
        VIDEO_INPUT_ENABLED_KEY: True,
        'modalities': ['text', 'video'],
    }
    cleanup_owned_settings_on_source_change(
        moving,
        old_source_type=ARK_PROVIDER_TYPE,
        new_source_type='openai_chat_completion',
    )
    assert VIDEO_INPUT_ENABLED_KEY not in moving
    assert moving['modalities'] == ['text', 'video']

    mid, hint = normalize_ark_model_metadata({'id': 'unknown'})
    assert mid == 'unknown'
    assert hint == {'id': 'unknown'}
    _, rich = normalize_ark_model_metadata({
        'id': 'rich',
        'modalities': {'input_modalities': ['image', 'audio']},
        'features': {'reasoning': {'supported': True}},
        'token_limits': {'context_window': 65536},
    })
    assert rich['modalities']['input'] == ['image', 'audio']
    assert rich['reasoning'] is True
    assert rich['limit'] == {'context': 65536}
    assert 'tool_call' not in rich

    base = {
        'id': 'same',
        'tool_call': True,
        'modalities': {'input': ['image'], 'output': ['text']},
        'limit': {'context': 131072, 'output': 0},
    }
    incoming = {
        'id': 'same',
        'tool_call': False,
        'modalities': {'input': ['audio']},
        'limit': {'context': 65536, 'output': 4096},
    }
    merged = _merge_source_feedback(base, incoming)
    assert merged['tool_call'] is True
    assert merged['modalities']['input'] == ['image', 'audio']
    assert merged['limit'] == {'context': 131072, 'output': 4096}

    payload = {
        'config_schema': {'provider': {'items': {}}},
        'provider_sources': sources,
        'providers': [
            {'id': 'ark/a', 'provider_source_id': 'ark', 'model': 'same'},
            {'id': 'foreign/a', 'provider_source_id': 'foreign', 'model': 'same'},
        ],
    }
    out = _inject_model_card_video_control(payload)
    assert out['providers'][0][VIDEO_INPUT_ENABLED_KEY] is False
    assert VIDEO_INPUT_ENABLED_KEY not in out['providers'][1]

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

    async def fake_resolve(ref: str) -> str:
        assert ref == '/tmp/test.mp4'
        return 'data:video/mp4;base64,AAAA'

    import astrbot_plugin_volcengine_provider.adapters.video as video_adapter
    original = video_adapter.resolve_video_reference
    video_adapter.resolve_video_reference = fake_resolve
    try:
        import asyncio
        marker = '[Video Attachment: name test.mp4, path /tmp/test.mp4]'
        messages = [{'role': 'user', 'content': [{'type': 'text', 'text': marker}]}]
        asyncio.run(video_adapter.inject_current_request_videos(
            messages,
            [TextPart(text=marker)],
            enabled=True,
        ))
        assert messages[0]['content'][0]['type'] == 'video_url'

        messages_off = [{'role': 'user', 'content': [{'type': 'text', 'text': marker}]}]
        asyncio.run(video_adapter.inject_current_request_videos(
            messages_off,
            [TextPart(text=marker)],
            enabled=False,
        ))
        assert messages_off[0]['content'] == [{'type': 'text', 'text': '[Video]'}]
    finally:
        video_adapter.resolve_video_reference = original

    print('FEEDBACK_BOUNDARY_0_1_15=OK')


if __name__ == '__main__':
    main()
