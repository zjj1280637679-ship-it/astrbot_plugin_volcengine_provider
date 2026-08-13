# Design Decisions

Lifecycle role: **WARM stable constraints + rejected-strategy memory**.

This file does **not** define the current release goal or active validation frontier. Read `docs/PROJECT_STATE.json` for HOT state and `docs/KNOWLEDGE_LIFECYCLE.md` for lifecycle rules.

## Purpose

Record objective conditions, durable design constraints, and rejected strategies so future maintainers/AI do not reconstruct intent from old field names or accidentally revive a previously falsified approach.

## Stable project scope

The plugin is an AstrBot provider integration for Volcengine Ark and Agent Plan. It may adapt provider-specific request/response protocols and media payloads that AstrBot does not natively express.

It is not intended to become:

- a second AstrBot provider lifecycle;
- a second fallback/retry/router;
- a global model-capability database;
- a permanent model-ID capability oracle;
- an independent Dashboard configuration system.

## Durable objective conditions

### Volcengine provider identity does not imply model identity

Ark serves both first-party Doubao/Seed and third-party/open models. Provider identity cannot safely imply a complete model capability set.

### Capability facts have scope and lifetime

Model behavior can drift because of model revisions, aliases, serving changes, account/region availability, provider API changes, and third-party packaging. Static `model_id -> capability` priors can become stale false certainty.

### AstrBot already owns mature lifecycle/policy layers

AstrBot owns provider source/model-card management, provider lifecycle, routing/fallback/retry, metadata display, Dashboard rendering, and relevant media resolution. The plugin should integrate rather than duplicate.

### Feedback is evidence, not permanent truth

A badge or `/models` field is useful but incomplete. Missing feedback is not `false`; positive feedback does not prove the complete QQ product path.

### Runtime failure provenance matters

Local media/payload transport failure, upstream explicit rejection, test-harness failure, and workflow teardown failure are distinct categories. One must not overwrite another's verdict.

### Interaction does not grant judgment authority

A component may have enough information to receive/translate/send/display something without authority to make a global capability judgment.

### Historical validation is impact-scoped

Historical QQ-oriented media success remains evidence until a dependency edge in `REGRESSION_SCOPE` changes. A direct WAV/MP4 fixture is not a substitute for the QQ/NapCat/AstrBot path.

## Dashboard boundary — corrected scope

### What ADR-0003 actually rejects

AstrBot 4.26/4.27's **shared top capability/modalities schema instance** does not provide a reliable provider-specific identity boundary for adding a fifth Volcengine video capability checkbox/icon. Earlier attempts could make that control appear for every provider or none.

0.1.20 identified a narrower boundary: the Provider dialog first deep-clones that schema and then has the selected Source type. The plugin may adapt that private clone for Ark/Agent Plan without modifying the shared instance. ADR-0006 governs this correction.

### What ADR-0003 does not reject

It does **not** mean every model-edit field is globally rigid.

Ordinary saved-model edit-body rows are rendered from keys actually present on the model object. Therefore provider-owned horizontal request fields can be projected onto owned model-card copies without modifying the shared top capability row. 0.1.19 uses this narrower path.

This distinction prevents an old correct statement from drifting into a false global rule:

```text
Rejected generalization:
"generic model cards cannot have provider-specific settings"

Correct scope:
"the shared top capability/modalities expansion is not a reliable provider-specific extension boundary;
ordinary owned model-edit body rows can be projected safely when the current model/source identity is known"
```

See ADR-0005.

## Stable strategy constraints

These constrain the current strategy in `PROJECT_STATE`; they do not replace it.

### Request/config versus capability

Provider-specific request settings may control how a request is sent. For an owned model card, explicit user membership of `video` in the current dialog's `modalities` list is configuration and may be mirrored into the plugin runtime boolean; it must not be promoted into permanent model capability truth or used to mutate the shared schema.

### Dynamic Ark feedback

Ordinary Ark `/models` feedback remains Source-scoped, current-response-only, single-use, async-context isolated, and non-persistent in plugin-owned global metadata. Explicit current `false`, empty lists, integer `0`, and unknown/future modality tokens remain information when upstream returns them.

### 0.1.18 Source video UI contract (historical compatibility)

The released 0.1.18 Source presentation control remains a stable compatibility contract:

- `volcengine_video_controls_visible` is presentation-only;
- the selector is exact-current-Source scoped;
- saved truth remains per-card `volcengine_video_input_enabled`;
- hiding the selector preserves choices/runtime state;
- foreign Sources do not receive the UI;
- AstrBot `modalities` remain unchanged;
- Source-save rollback preserves the original host error and only claims layers actually restored.

This remains migration and historical evidence. Its visible Source master/selector is retired in 0.1.20; old values are preserved as user intent and cleaned after migration.

### Migration

Migration preserves user configuration intent, not model facts. Wrong-Source/foreign debris must not be promoted. Historical precedence and 0.1.18 transaction behavior remain documented in ADR-0004 and `TEST_HISTORY`.

### Testing

- contract/unit tests judge plugin-owned invariants;
- AstrBot service tests judge host integration;
- real Dashboard automation judges presentation/interaction only;
- raw Ark tests judge downstream protocol attribution;
- QQ compatibility requires the QQ-equivalent product path;
- workflow teardown/cache failures are harness failures unless they prevent the product evidence from running.

## Rejected strategies / 假策略墓地

These remain COLD/rejected unless an explicit reconsideration condition fires.

### Static model-ID capability completion — rejected

Reason: third-party/open models, aliases, serving changes, and future revisions provide legitimate counterexamples.

Reconsider only if Ark exposes an authoritative, scoped, freshness-defined capability protocol that the plugin can consume without inventing permanent priors.

### Provider-wide video capability flag — rejected

Reason: one Source can host multiple models; provider-wide runtime truth polluted unrelated cards and conflicted with host semantics.

Do not confuse this with `volcengine_video_controls_visible`, which is presentation-only.

### Writing transient provider feedback into global `LLM_METADATAS[model_id]` — rejected

Reason: model IDs are not globally unique provider identities and stale data can cross Source/provider boundaries.

### Treating missing feedback as `false` — rejected

Reason: absence is not a negative observation and can conceal transport/account/provider causes.

### Plugin-local fallback/routing — rejected

Reason: AstrBot already owns routing/fallback/retry; duplicate state machines conflict.

### Extending the shared schema instance as the general provider-specific field mechanism — rejected

Reason: the shared schema instance lacks the reliable provider identity needed for isolated fifth-checkbox behavior. This does not reject adapting a private per-dialog clone after the selected Source type is known.

Important: this does **not** reject ordinary saved-model edit-body fields.

### Making fine UI automation a capability or release truth oracle — rejected

Reason: selectors/DOM can drift while service/runtime behavior remains valid. UI automation is presentation evidence and should not overwrite stronger layer-specific verdicts.

### Broadening media code to satisfy non-equivalent fixtures — rejected

Reason: a green direct-provider fixture can coexist with a broken QQ path, and a red synthetic fixture can be irrelevant to unchanged product behavior.

### Duplicating current release state across documentation — rejected by ADR-0005

Reason: independent present-tense copies accumulate drift. `PROJECT_STATE` is the single HOT authority; other docs retain constraints/history only.

## Validation philosophy

A correct rule must survive both directions:

- positive path: legitimate supported behavior remains reachable;
- counterexample path: the rule must not destroy another legitimate path.

Every conclusion should be traceable to an interface that can actually support it, and every historical conclusion should have a lifecycle role. If it is not HOT in `PROJECT_STATE`, it must not silently drive the next implementation step.
