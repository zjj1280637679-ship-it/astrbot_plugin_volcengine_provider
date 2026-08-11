# ADR-0004: Migration preserves user intent, not model facts

## Status

Accepted for 0.1.15.

## Context

Earlier plugin versions encoded video-related user choices in Source-level booleans, legacy per-model fields, and at one point `modalities: video`. These encodings are historical configuration representations, not reliable model-capability truth.

A migration bug showed why truthiness-based fallback is dangerous: an explicit legacy Source `false` could be skipped and an older `modalities: video` clue could silently re-enable video transport.

## Decision

Migration carries forward the user's prior configuration intent into the new per-model request-transport switch.

Precedence:

1. current per-card `volcengine_video_input_enabled`;
2. legacy per-card `volcengine_model_video_input`;
3. legacy explicit Source boolean (`volcengine_ark_video_input` / `volcengine_agent_plan_video_input`), including explicit `false`;
4. historical `modalities: video` only as the final migration clue.

Presence is checked independently from truthiness so `false` remains explicit information.

AstrBot `modalities` itself is preserved unchanged; migration does not rewrite the host's feedback/config state.

## Rejected alternative

Treating the newest-looking historical signal as a model fact or using truthy fallback ordering.

## Consequences

Upgrade preserves user choice without claiming that the migrated value proves model capability. Migration remains a compatibility boundary rather than a capability-discovery mechanism.
