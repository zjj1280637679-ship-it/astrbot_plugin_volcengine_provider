# ADR-0003: Concrete model-card scope is the Dashboard isolation boundary

## Status

Accepted/current.

## Context

AstrBot's provider/model configuration schema is shared across Provider types. A Volcengine-specific field or fifth modality added unconditionally to that shared surface can leak into unrelated Provider cards. At the same time, hiding the field before a concrete card's Source identity is known can make the required control disappear everywhere.

The reliable identity is the concrete model card's `provider_source_id`, resolved against `provider_sources[].type`.

## Decision

Provider-specific model-card UI is adapted only after concrete ownership is known.

For cards whose Source type is `volcengine_ark_chat_completion` or `volcengine_agent_plan_chat_completion`:

- the card-local/private `modalities` metadata may expose exactly one additional native `video` option;
- the card-local request metadata may expose the typed Volcengine request fields;
- AstrBot's native `custom_extra_body` remains present.

For every foreign Provider card:

- no plugin Video option;
- no `volcengine_*` request rows;
- no plugin fields persisted.

A Provider Source master switch or model selector is not a substitute for the concrete-card control. A process-global/shared-schema Video fallback that can visually appear on foreign cards is forbidden.

The compiled-asset bridge and runtime-component bridge are complementary implementations of the same concrete-object rule. They must be reversible and fail closed when the required ownership/boundary cannot be identified safely.

## Saved truth

For an owned card, native `modalities` membership is the user-facing Video state. `volcengine_video_input_enabled` is only a compatibility/runtime mirror.

## Acceptance

The exact release candidate must prove in a real AstrBot Dashboard that Ark and Agent Plan cards each show one Video checkbox, a visible-label click checks it, save/reopen and process restart preserve it, request rows remain visible/persistent, foreign cards stay clean, and uninstall removes plugin-owned UI residue.

Static schema inspection or successful bridge installation alone is insufficient.

## Historical note

Earlier Source-page and shared-schema fallback strategies are superseded. Their exact text remains in Git history and is not current design authority.
