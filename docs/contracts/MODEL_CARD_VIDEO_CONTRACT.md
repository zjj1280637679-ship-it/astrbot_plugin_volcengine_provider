# Source-scoped model-card Video contract

Status: **non-negotiable product contract** for the recovered model-card Video capability, with the 0.1.23 delivery-resilience amendment.

This document exists to prevent future refactors, migrations, AI-generated patches, or UI cleanups from confusing an AstrBot **Provider Source / supplier-wide control** with the **capability selector of one concrete model card**, while also preventing a repeat of the 0.1.22 failure mode where a correct private-clone patch existed but a real installation could continue using a stale Dashboard bundle and therefore show no Video control at all.

## The object that owns the switch

`Video` / `视频` belongs to the native AstrBot `modalities` checklist of **one concrete model card**.

The preferred exact presentation path is:

1. AstrBot is creating or editing one concrete model-card instance;
2. that card resolves to a Provider Source whose `type` is one of this plugin's two owned source types:
   - `volcengine_ark_chat_completion`;
   - `volcengine_agent_plan_chat_completion`;
3. the UI is operating on the model dialog's **private schema clone**, after the selected Source type is known;
4. that private owned clone exposes exactly one fifth native `video` option alongside Text, Image, Audio, and Tool use.

The Provider Source page itself is not the owner of this switch. The user's saved truth remains the concrete model card's native `modalities` list.

## 0.1.23 delivery-resilience amendment

The precise private-clone path remains the target behavior, but **UI disappearance is no longer the accepted fallback** when a browser has cached an older Dashboard bundle or the compatible transformed asset is not re-requested.

0.1.23 therefore permits one narrowly bounded backend fallback:

- the shared `provider.items.modalities` metadata may receive one additional `video` option **only when it is explicitly marked as this plugin's delivery fallback**;
- the marker must distinguish plugin-inserted fallback Video from any future AstrBot-native Video support;
- a compatible private-clone frontend bridge must remove the marked fallback Video from foreign Provider dialogs and keep it on the two owned Volcengine Source types;
- if the precise frontend bridge does not execute, temporary foreign **visual** exposure of the marked Video option is an accepted degradation rather than total disappearance on the owned card;
- foreign create/update boundaries must strip `video` from the submitted `modalities` before host persistence, so this visual degradation cannot become foreign persisted state or foreign request behavior;
- plugin release/unload must restore the wrapped host methods and remove plugin-owned temporary Dashboard assets;
- the fallback must not delete, rewrite, or reinterpret a future host-native Video modality that does not carry the plugin fallback marker.

This exception exists only for delivery robustness. It is **not** permission to turn shared schema metadata into a second capability database, supplier-wide switch, or permanent cross-provider Video truth.

## Forbidden substitutions

The feature is **not** satisfied by any of the following:

- an unmarked/unbounded process-global `video` injection with no foreign save guard;
- a Provider Source master switch or supplier-wide visibility switch;
- a Source-page model selector;
- a custom request-body field, hidden boolean, explanatory row, or plugin-only checkbox outside native `modalities`;
- a checkbox that exists only during creation but cannot be restored during edit;
- model metadata saying a model can accept video;
- a successful video request when the model-card switch is absent or ignored;
- unit tests that never exercise the real Dashboard ownership boundary;
- deleting the 0.1.19+ rich model-card request fields, audio path, video quality modes, Agent Plan path, migration logic, or request overrides merely to simplify Video delivery.

A backend shared-schema mutation is acceptable **only** when it satisfies every bounded-fallback condition above. A generic shared-schema Video injection without marker, precise cleanup path, foreign persistence guard, reversibility, and regression tests remains prohibited.

## Persistence and runtime truth

The user's current model-card selection is represented by AstrBot's native `modalities` list.

- Saving an owned card with `video` in `modalities` means video input is enabled for **that card**.
- Saving the same owned card without `video` means video input is disabled for **that card**.
- A fallback Video value submitted from a foreign card must be removed before persistence.
- Compatibility mirrors such as `volcengine_video_input_enabled` may exist only as runtime/migration mirrors; they must never become a second user-facing source of truth that can disagree with owned-card `modalities`.
- Reopening the owned card must reconstruct the native Video checkbox from persisted card state.

At request time, the current owned card's persisted setting controls the video transport path:

- enabled: trusted current-request AstrBot video attachment envelopes are converted to Ark-compatible `video_url` content;
- disabled: that conversion does not run and the attachment remains a non-video placeholder for the model request.

Foreign Provider requests are outside this plugin's video transport ownership and must not gain plugin Video behavior from the fallback.

## Acceptance gates

### Preferred exact-path five-condition gate

On every AstrBot/Dashboard version that matches the precise bridge, all five conditions must pass together:

1. **Correct object appears** — Ark and Agent Plan model create/edit dialogs expose exactly one native Video option alongside Text, Image, Audio, and Tool use.
2. **Wrong objects stay clean** — OpenAI, xAI, Gemini, and other foreign Provider model dialogs do not expose the plugin fallback Video; Provider Source pages do not substitute a master switch/selector for it.
3. **Save/reopen persists** — after a real user selection is saved, close/reopen, Dashboard refresh, AstrBot restart, and compatible plugin update preserve that owned card's value.
4. **Runtime follows the selection** — enabled and disabled owned cards produce different request behavior exactly as specified above.
5. **Uninstall/release leaves no public-UI residue** — every plugin-owned Dashboard/service wrapper is reversible; after release/unload the host methods/assets are restored and plugin fallback metadata no longer exists.

### Degraded-delivery fallback gate

If the precise frontend bridge cannot execute, the fallback is healthy only when all of these hold:

1. the shared schema contains exactly one **marked** fallback `video` option so owned cards do not lose the control;
2. any foreign visual Video selection is stripped at foreign create/update persistence boundaries;
3. no foreign plugin runtime mirror is created and no foreign request is routed through the plugin's Video adapter;
4. future host-native unmarked Video is left untouched;
5. release/unload restores the host and removes plugin temporary assets.

The degraded gate does not redefine foreign visual pollution as ideal behavior; it records a deliberately accepted side effect in exchange for keeping the owned-card function available.

## Current implementation boundary

The 0.1.23 candidate follows this architecture:

- `capabilities/video_modality_fallback.py` adds the marked reversible shared-schema delivery fallback and strips fallback Video from foreign create/update payloads;
- `capabilities/dashboard_asset_bridge.py` remains the preferred source-scoped private-clone adapter, removes marked fallback Video from foreign clones, preserves it for owned clones, and serves a copied index with a content-derived query suffix so stale cached Dashboard bundles do not satisfy the new request;
- `capabilities/model_fields_bridge.py` projects/saves the existing rich owned-card request fields and strips plugin fields from foreign cards;
- `capabilities/model_fields.py` maps native owned-card `modalities` membership to the per-card compatibility/runtime mirror and preserves the 0.1.19+ request-field semantics;
- `capabilities/model_scope.py` resolves ownership from `provider_source_id -> provider_sources[].type`;
- `adapters/video.py` performs the actual enabled/disabled transport behavior and is unchanged by the 0.1.23 delivery repair;
- release functions restore host methods/static resolution and delete plugin-owned temporary assets.

The candidate is additionally required to pass a real same-endpoint/same-key/same-model source-type differential: an AstrBot-native OpenAI Source pointed at the Ark endpoint must remain without plugin Video on the precise path, while the plugin Ark Source using the same real model exposes Video and persists it.

## Recovery anchor

The original recovered 0.1.22 source remains frozen at branch:

`archive/model-card-video-known-good-0.1.22`

Do not delete or reinterpret that branch as the new fallback implementation. It remains the regression anchor for the precise source-scoped model-card Video path; 0.1.23 adds a delivery-resilience layer around it rather than replacing its runtime semantics.
