# ADR-0004: Migration preserves user intent, not model facts

## Status

Accepted for 0.1.15; amended for the 0.1.17 Dashboard projection upgrade path.

## Context

Earlier plugin versions encoded video-related user choices in Source-level booleans, legacy per-model fields, and at one point `modalities: video`. These encodings are historical configuration representations, not reliable model-capability truth.

A migration bug showed why truthiness-based fallback is dangerous: an explicit legacy Source `false` could be skipped and an older `modalities: video` clue could silently re-enable video transport.

AstrBot 4.26.1 exposed live provider dictionaries through its schema service. The retired 0.1.17 model-card projection could therefore leave `_volcengine_video_transport_ui_<source-id-as-hex>` on a real model card before another config save. That value is user intent only when it is a boolean and its encoded Source ID exactly matches the card's own `provider_source_id`. A same-prefix key for another Source, a forged foreign key, or the field on the wrong object layer is debris, not intent.

## Decision

Migration carries forward the user's prior configuration intent into the new per-model request-transport switch.

Precedence:

1. current per-card `volcengine_video_input_enabled`;
2. retired 0.1.17 `_volcengine_video_transport_ui_<source-hex>` only when the value is boolean and `<source-hex>` exactly encodes that card's current `provider_source_id`;
3. legacy per-card `volcengine_model_video_input`;
4. legacy explicit Source boolean (`volcengine_ark_video_input` / `volcengine_agent_plan_video_input`), including explicit `false`;
5. historical `modalities: video` only as the final migration clue.

Presence is checked independently from truthiness so `false` remains explicit information.

AstrBot `modalities` itself is preserved unchanged; migration does not rewrite the host's feedback/config state.

After resolving precedence, migration removes every retired model-dialog key, new Source-selector temporary key, and wrong-layer plugin video field. A wrong-Source retired key cannot be promoted; foreign cards cannot acquire canonical Volcengine state from any forged canonical/legacy/temporary field. On Sources, only `volcengine_video_controls_visible` may persist, and only for an owned Volcengine Source.

## Rejected alternative

Treating the newest-looking historical signal as a model fact, accepting any same-prefix temporary key without exact Source identity, promoting foreign/wrong-layer state, or using truthy fallback ordering.

## Consequences

Upgrade preserves the exact owned-card user choice without claiming that the migrated value proves model capability. It also heals the known AstrBot 4.26.1 / 0.1.17 live-schema residue and removes non-authoritative debris. Migration remains a compatibility boundary rather than a capability-discovery mechanism.
