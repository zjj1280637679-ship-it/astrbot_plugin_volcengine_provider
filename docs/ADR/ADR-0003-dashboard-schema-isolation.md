# ADR-0003: Dashboard schema must isolate provider-owned UI

## Status

Accepted for 0.1.15; amended for the current Source-page selector design.

## Context

AstrBot model-card schema is shared. Adding an unconditional Volcengine-specific field to the shared schema can cause that field to appear on unrelated providers. Conversely, conditioning it on Provider identity that the generic model-card component does not actually own can hide it everywhere. AstrBot provider types also use different Dashboard layouts, so schema visibility is part of product correctness, not merely presentation.

The Provider Source form owns the current Source identity and type. It is therefore the reliable isolation boundary for a provider-owned configuration surface, even though the saved runtime truth remains per model card.

## Decision

Do not expose the canonical `volcengine_video_input_enabled` field as an unconditional shared model-card schema item.

Do not expose a video control in the generic model-card projection. For each owned Volcengine Source, expose on the Source page:

- persistent `volcengine_video_controls_visible`, whose only authority is whether the model-selection area is shown;
- a temporary checkbox selector built from model-card IDs belonging to that exact Source and guarded by the persistent display preference.

The selector key uses a reversible UTF-8-to-hex encoding of the Source ID so identity is not truncated or probabilistically hashed. When the selector is visible and submitted, the Source save boundary writes the chosen IDs to each matching card's canonical `volcengine_video_input_enabled`, then removes the temporary selector before Source persistence. When the display preference is false, or the hidden selector is omitted, existing per-card values are left untouched. Closing the UI therefore hides configuration only; it does not clear selections or disable runtime video transport.

Before translating a selector, the bridge snapshots the complete model-card list. If the host Source upsert rejects or raises after translation, the bridge restores that snapshot and re-raises the original error. UI projection must not turn a failed Source save into partially committed in-memory card state.

Foreign Sources receive neither field. A stale already-open 0.1.17 model dialog may still use the retired model-card temporary key at create/update save time, but this is compatibility behavior rather than the current visible UI.

If the host lacks the complete `get_provider_schema` + `upsert_provider_source` API set needed to preserve the Source save contract, the UI enhancement is not exposed. Other independently safe bridge hooks may still operate.

## Required invariants

- foreign providers do not display the Volcengine field;
- generic model cards display neither the canonical nor retired temporary Volcengine field;
- `volcengine_video_controls_visible=false` preserves every per-card transport value;
- the selector lists and updates only cards owned by the exact Source, using card IDs rather than model names;
- temporary Source selector keys do not persist;
- a forged temporary key on a foreign Source cannot create Volcengine state;
- Source/model-card field ownership remains distinct;
- Source-save semantics are tested on both AstrBot 4.26.1 and 4.27.2;
- host Source-save failure restores the complete pre-call model-card list and propagates the original error;
- layout correctness must be checked against the real AstrBot Dashboard Source layout, not schema/service data alone.

## Consequences

The implementation is more explicit than one global schema field, but it avoids cross-provider UI pollution and preserves one per-card runtime truth. The real 4.26.1/4.27.2 service matrix supplies L3 save-boundary evidence. A separate 2026-08-12 real AstrBot 4.27.2 Dashboard DOM run supplies L4 presentation evidence: Ark/Plan each had one master and a selector scoped to their own 2/1 cards; closing hid it, reopening preserved the selection with zero API requests; foreign had 0/0; every Ark/Plan/foreign generic model dialog omitted canonical, retired temporary, and new temporary video fields; `pageErrors=[]`.
