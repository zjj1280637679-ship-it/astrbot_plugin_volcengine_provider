# Provider × Host × Product Evidence Matrix

## Purpose

This document defines which validation layer is allowed to prove which claim. The project deliberately separates code correctness, AstrBot integration, Dashboard reachability, downstream Ark protocol behavior, and QQ product compatibility.

A green lower-layer test must not be promoted into a stronger claim than its interface supports.

## Evidence layers

### L2 — local contract/regression

Validates plugin-owned invariants such as:

- migration precedence;
- foreign-provider isolation;
- Source selector projection, per-card write-back, hidden-state preservation, and temporary UI-key removal;
- transient `/models` feedback semantics;
- failure provenance;
- trusted video-marker behavior.

This layer cannot prove AstrBot runtime integration or QQ compatibility.

### L3 — real AstrBot service integration

Validates the actual supported host API path, including the declared minimum AstrBot version where relevant:

- Provider registration;
- `ProviderConfigService` create/update/save boundaries;
- `ProviderConfigService.upsert_provider_source` selector save boundaries;
- optional Dashboard API capability detection;
- host/provider compatibility.

This layer proves host integration, not model capability.

### L4 — real Dashboard reachability and presentation evidence

Hard gate:

- real AstrBot Dashboard can build/start;
- login succeeds;
- Provider page is reachable with the plugin loaded.

Non-blocking presentation evidence:

- screenshots;
- semantic DOM/visible text;
- layout snapshots.

For the current video design, L4 must directly observe that an owned Volcengine Source shows “显示逐模型视频选项”, that opening it reveals only that Source's model-card checkbox list, and that foreign Sources and generic model cards show no Volcengine video field. The 4.26.1/4.27.2 service matrix does not prove this presentation.

The dated 2026-08-12 real AstrBot `4.27.2` Dashboard DOM run supplies this L4 evidence: Ark and Agent Plan each showed exactly one master; opening produced exactly one selector containing only that Source's 2 and 1 cards respectively; closing hid the selector, reopening preserved the choice, and the interaction issued zero API requests; foreign Source showed 0 masters and 0 selectors; Ark, Plan, and foreign generic model dialogs contained none of `volcengine_video_input_enabled`, the retired model-card temporary key, or the new Source-selector temporary key; `pageErrors=[]`.

Fine Playwright selector choreography is **not** a release authority. Previous failures from welcome overlays, labels, fixed Source IDs, or Vuetify selector assumptions were test-harness evidence, not plugin-runtime evidence.

### L5 — downstream Volcengine protocol attribution

Where a real credential and meaningful fixture exist, compare a minimal raw upstream request with the same logical path through the plugin.

Useful cases:

- ordinary Ark `/models`;
- text;
- image;
- endpoint/authentication attribution;
- a media request only when the fixture actually tests the adapter contract being investigated.

Interpretation:

```text
raw success + plugin success
  -> downstream protocol and plugin path both worked under current conditions

raw success + plugin failure
  -> plugin path is suspect and production code may need investigation

raw failure + plugin failure
  -> upstream/account/model/test-condition boundary remains plausible;
     do not blame plugin code without further attribution
```

L5 is still not automatically QQ product compatibility.

### L6 — QQ-equivalent product path

For QQ media features the product interface is approximately:

```text
QQ event
  -> NapCat / OneBot
  -> AstrBot event/media lifecycle
  -> MediaResolver
  -> plugin audio/video last mile
  -> Ark request
  -> provider/model response
```

This is the layer that can validate QQ-oriented audio/video compatibility.

A generated WAV or MP4 sent directly to a Provider is not equivalent to this path. Production code must not be broadened merely to make a non-equivalent raw fixture pass.

## Provider identities

Both plugin-owned providers currently register as AstrBot `chat_completion` providers:

- `volcengine_ark_chat_completion`;
- `volcengine_agent_plan_chat_completion`.

Agent Plan is **not** an `agent_runner` card. Tests and UI evidence must follow the actual registered host type rather than an early conceptual model.

## Required invariants

### Capability/feedback

- no static model-ID capability oracle;
- missing feedback remains unknown;
- explicit current `false`, empty list, and `0` remain current observations when upstream returned them;
- future/unknown modality tokens are not deleted merely because the current plugin cannot interpret them;
- current dynamic Ark feedback does not persist into global `LLM_METADATAS[model_id]`.

### Dashboard/config isolation

- generic model-card projections do not expose the canonical or retired temporary Volcengine video transport field;
- only owned Volcengine Sources receive persistent `volcengine_video_controls_visible` and a Source-specific temporary model selector;
- the visibility preference controls display only: hiding the selector preserves per-card canonical choices and runtime behavior;
- an open selector saves by exact model-card ID back to `volcengine_video_input_enabled` on cards belonging to that exact Source;
- temporary selector keys never survive Source persistence;
- foreign Sources do not receive these fields, and forged foreign temporary keys cannot create Volcengine state;
- if the host Source upsert fails after selector translation, the complete pre-call model-card list is restored and the original error propagates;
- optional host Dashboard APIs degrade only the enhancement they own.

These Source-save invariants have passed the real AstrBot `4.26.1` and `4.27.2` service matrix (L3). Current Source-page presentation separately passed the dated 2026-08-12 real AstrBot `4.27.2` Dashboard DOM run (L4) with the exact isolation, conditional visibility, preserved client selection, zero-request interaction, and no-page-error observations recorded above. Neither result is model-capability or QQ media-path evidence.

### Migration

Precedence:

1. current per-card `volcengine_video_input_enabled`;
2. retired 0.1.17 `_volcengine_video_transport_ui_<source-hex>` only when it is boolean and the encoded Source exactly matches the card's `provider_source_id`;
3. legacy per-card `volcengine_model_video_input`;
4. legacy explicit Source boolean, including `false`;
5. historical `modalities: video` only as the last migration clue.

Wrong-Source retired keys and every plugin video field on a foreign card are cleanup-only and never become canonical state. After resolution, all retired, temporary, and wrong-layer plugin fields are removed; AstrBot `modalities` itself remains unchanged.

### Failure provenance

- local media/input transport failure records `reached_model=false` and no capability verdict;
- upstream rejection stays on the upstream/AstrBot error path;
- the plugin does not add model switching or fallback decisions.

## Historical media regression assets

QQ-oriented audio/video validations are indexed in `docs/TEST_HISTORY.md`. Whether they require a full rerun is decided by `docs/REGRESSION_SCOPE.md`, not by a rule that every release must repeat every historical E2E.

A full QQ-equivalent rerun is required when the relevant media adapter, AstrBot media contract, Ark media payload contract, or QQ/NapCat input semantics change materially.

## Evidence summary format

```text
Plugin contracts
  feedback semantics                     PASS/FAIL
  migration precedence                   PASS/FAIL
  foreign-provider isolation             PASS/FAIL
  failure provenance                     PASS/FAIL

AstrBot integration
  4.26.1 declared-minimum integration    PASS/FAIL
  4.27.2 integration                     PASS/FAIL
  Dashboard coarse reachability          PASS/FAIL
  Source video UI presentation (L4)      PASS/FAIL/PENDING(reason)

Current downstream attribution
  ordinary Ark /models                   PASS/FAIL/SKIP(reason)
  ordinary Ark text                      PASS/FAIL/SKIP(reason)
  ordinary Ark image                     PASS/FAIL/SKIP(reason)
  Agent Plan credential/path attribution PASS/FAIL/SKIP(reason)

QQ product regressions
  audio                                  HISTORICAL_VALID / REVALIDATED / STALE(reason)
  video                                  HISTORICAL_VALID / REVALIDATED / STALE(reason)
```

A `SKIP` must include a reason. Historical evidence must not be silently upgraded to a current result, but it also must not be silently erased.
