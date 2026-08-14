# Source-scoped model-card Video contract

Status: **non-negotiable product contract** for the recovered 0.1.22 implementation.

This document exists to prevent future refactors, migrations, AI-generated patches, or UI cleanups from confusing an AstrBot **Provider Source / supplier-wide control** with the **capability selector of one concrete model card**.

## The object that owns the switch

`Video` / `视频` belongs to the native AstrBot `modalities` checklist of **one concrete model card**.

It may appear only when all of the following are true:

1. AstrBot is creating or editing one concrete model-card instance;
2. that card resolves to a Provider Source whose `type` is one of this plugin's two owned source types:
   - `volcengine_ark_chat_completion`;
   - `volcengine_agent_plan_chat_completion`;
3. the UI is operating on the model dialog's **private schema clone**, after the selected Source type is known.

The Provider Source page itself is not the owner of this switch.

## Forbidden substitutions

The feature is **not** satisfied by any of the following:

- adding `video` to AstrBot's process-global/shared `provider.items.modalities` schema;
- a Provider Source master switch or supplier-wide visibility switch;
- a Source-page model selector;
- a custom request-body field, hidden boolean, explanatory row, or plugin-only checkbox outside native `modalities`;
- a checkbox that exists only during creation but cannot be restored during edit;
- model metadata saying a model can accept video;
- a successful video request when the model-card switch is absent or ignored;
- unit tests that never exercise the real Dashboard ownership boundary.

A backend-only mutation of the shared Provider schema is specifically prohibited: at that layer the currently selected Source type is not sufficient to isolate the native modality option, so such a change can leak `Video` into OpenAI, xAI, Gemini, or other foreign Provider model cards.

## Persistence and runtime truth

The user's current model-card selection is represented by AstrBot's native `modalities` list.

- Saving an owned card with `video` in `modalities` means video input is enabled for **that card**.
- Saving the same card without `video` means video input is disabled for **that card**.
- Compatibility mirrors such as `volcengine_video_input_enabled` may exist only as runtime/migration mirrors; they must never become a second user-facing source of truth that can disagree with `modalities`.
- Reopening the card must reconstruct the native Video checkbox from persisted card state.

At request time, the current card's persisted setting controls the video transport path:

- enabled: trusted current-request AstrBot video attachment envelopes are converted to Ark-compatible `video_url` content;
- disabled: that conversion does not run and the attachment remains a non-video placeholder for the model request.

## Five-condition joint acceptance gate

The core feature exists only when **all five** conditions pass together:

1. **Correct object appears** — Ark and Agent Plan model create/edit dialogs expose exactly one native Video option alongside Text, Image, Audio, and Tool use.
2. **Wrong objects stay clean** — OpenAI, xAI, Gemini, and every other foreign Provider model dialog do not expose the plugin's Video option; Provider Source pages do not substitute a master switch/selector for it.
3. **Save/reopen persists** — after a real user selection is saved, close/reopen, Dashboard refresh, AstrBot restart, and compatible plugin update preserve that card's value.
4. **Runtime follows the selection** — enabled and disabled cards produce different request behavior exactly as specified above.
5. **Uninstall/release leaves no public-UI residue** — every plugin-owned Dashboard/service wrapper is reversible; after release/unload the host methods/assets are restored and no fifth global modality remains.

A release gate or code review must not declare this feature healthy from a proper subset of these conditions.

## Recovered implementation boundary

The known-good 0.1.22 implementation follows this architecture:

- `capabilities/dashboard_asset_bridge.py` patches only the already-created private model-dialog schema clone, where `selectedProviderSource.type` is known;
- `capabilities/model_fields_bridge.py` projects/saves owned-card values and strips plugin fields from foreign cards;
- `capabilities/model_fields.py` maps native `modalities` membership to the per-card compatibility/runtime mirror;
- `capabilities/model_scope.py` resolves ownership from `provider_source_id -> provider_sources[].type`;
- `adapters/video.py` performs the actual enabled/disabled transport behavior;
- release functions restore host methods/static resolution and delete plugin-owned temporary assets.

If a future AstrBot Dashboard build changes the private-clone structure, the safe behavior is **fail closed and update the compatibility bridge/test**, not fall back to a shared-schema injection.

## Recovery anchor

The recovered source is frozen at branch:

`archive/model-card-video-known-good-0.1.22`

Do not delete or reinterpret that branch as a newer feature experiment. It is the regression recovery anchor for this contract.
