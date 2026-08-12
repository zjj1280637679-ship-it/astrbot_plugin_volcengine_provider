# Design Decisions

## Purpose

This file records the **objective conditions discovered during development**, the **expected outcomes**, and the **current strategy**. It exists so future maintainers and AI agents do not reconstruct project intent from field names or old implementation details alone.

The project must distinguish:

- what was observed,
- what is desired,
- what strategy currently satisfies the observed conditions,
- and what was rejected because a counterexample made it invalid.

## Project scope

The plugin is an AstrBot provider integration for Volcengine Ark and Agent Plan. It may adapt request/response protocols and media payloads that AstrBot does not natively express for this provider.

It is not intended to become:

- a second AstrBot provider lifecycle,
- a second fallback/retry/router,
- a global model capability database,
- a permanent model-ID capability oracle,
- or an independent Dashboard configuration system.

## Objective conditions discovered

### 1. Volcengine has more than one provider role

Volcengine/Ark is simultaneously:

- a first-party serving platform for Doubao/Seed models, and
- a cloud serving/aggregation platform for third-party or open models.

Therefore a provider identity does not imply that the provider plugin can correctly infer the complete capability set of every model exposed through that provider.

### 2. Model capability is not stable enough for plugin-local permanent priors

Model behavior may change because of:

- model revisions,
- serving-layer changes,
- account or regional availability,
- provider API changes,
- model aliases,
- packaging around third-party/open models,
- or future capabilities that do not exist when the current plugin is written.

A static `model_id -> capability` table can therefore become a source of stale false certainty.

### 3. AstrBot already owns mature mechanisms

AstrBot already owns major lifecycle and policy mechanisms including:

- provider source/model card management,
- provider lifecycle,
- fallback/retry/routing,
- metadata/capability feedback display,
- Dashboard schema rendering,
- media resolution in relevant paths.

A provider plugin should preferentially integrate with these mechanisms rather than duplicate them.

### 4. Capability feedback is incomplete by design

The presence of a capability icon or metadata field is useful feedback. Its absence does not prove lack of support. Likewise, a positive capability indication does not prove that the complete product path works.

For example, a model/API may support audio while QQ -> NapCat -> AstrBot -> MediaResolver -> provider transport is broken.

### 5. Different provider types and host paths can have different UI layouts

AstrBot's Dashboard does not reduce every provider to one uniform card. Provider Sources, model cards, conditions, advanced settings, and different provider types can have different layouts and interaction flows.

Therefore code-level equivalence or schema-level equivalence does not prove product-path equivalence. At the same time, UI automation must prove the interface it is driving instead of treating selector assumptions as product truth.

### 6. Runtime failure provenance matters

A request can fail before reaching the model, or after reaching the upstream provider/model.

- Local/media/payload transport failure must not be interpreted as model capability rejection.
- Upstream explicit modality rejection is a materially different observation.
- A test-harness failure is a third category and must not be silently attributed to product code.

The plugin should expose where a failure occurred without taking ownership of AstrBot's routing decision.

### 7. Interaction does not grant judgment authority

A component can have enough information to receive, translate, send, or display a request while still lacking enough information or authority to make a global conclusion.

Consequences:

- one success does not become permanent capability truth;
- one failure does not become permanent incapability truth;
- one UI badge does not become runtime policy;
- one raw Ark media fixture does not become proof of QQ compatibility.

The full reasoning boundary is documented in `docs/KNOWLEDGE_BOUNDARY.md`.

### 8. Historical validation must be impact-scoped

Audio/video product behavior is QQ-oriented. A convenient direct WAV/MP4 fixture exercises a different interface from the real QQ/NapCat/AstrBot media path.

Therefore:

- historical QQ-oriented media success remains evidence while relevant dependencies are unchanged;
- a full QQ-equivalent rerun is triggered by changes to the media adapter, host media contract, Ark media payload contract, or QQ/NapCat input semantics;
- unrelated metadata/UI/docs changes do not justify rewriting media code just to make a non-equivalent fixture pass.

See `docs/TEST_HISTORY.md` and `docs/REGRESSION_SCOPE.md`.

### 9. The generic model-card component is not a reliable Provider identity boundary

AstrBot 4.26/4.27 uses a shared model-card schema/rendering path. A Volcengine field added without a usable current-Source identity can therefore appear on every provider card; a condition evaluated against data that the card does not own can instead hide it everywhere.

The Provider Source form owns the current Source `id` and `type`, so it is the narrower configuration boundary for provider-owned controls. This does not move runtime truth to the Source: it only moves the editing surface to an object with reliable identity.

## Expected outcomes

The project should:

1. expose the request shapes and media transports it can correctly express to Volcengine;
2. preserve user choice about whether a transport path is attempted;
3. preserve AstrBot-native feedback rather than overwriting it with plugin guesses;
4. keep dynamic Ark feedback current and non-stale;
5. keep Volcengine-specific UI/config fields isolated from foreign providers;
6. preserve user intent through migrations;
7. allow future capability mechanisms to be added when they have a valid evidence/source protocol;
8. validate each claim at the layer that actually exercises the relevant interface;
9. preserve historical product-path evidence until impact analysis makes it stale;
10. keep project reasoning explicit enough for future humans and AI agents to reconstruct safely.

## Current strategy

### Video

`volcengine_video_input_enabled` is a **request transport switch on a model card**. It means the user allows the plugin to attempt video transport for that card. It is not a model capability declaration and must not be written into AstrBot `modalities`.

### Dynamic Ark model feedback

Ordinary Ark `/models` feedback is handled as:

- Source-scoped,
- current-response-only,
- single-use,
- async-context isolated,
- non-persistent in plugin-owned global metadata.

Explicit current values such as `false`, an empty list, or integer `0` remain information when the upstream explicitly returns them. Missing fields remain missing rather than being converted to a negative capability claim.

Unknown/future modality tokens are preserved rather than filtered through today's vocabulary.

### Dashboard Source UI

The canonical Volcengine video transport field is not installed as an unconditional shared model-card schema field and is removed from generic model-card projections.

For an owned Volcengine Source, the Dashboard bridge exposes:

- persistent `volcengine_video_controls_visible`, which controls only whether the selection area is shown;
- a temporary checkbox list containing the current Source's model-card IDs, visible only while that preference is `true`.

Saving an open selector writes the chosen IDs back to each card's canonical `volcengine_video_input_enabled`, then strips the temporary selector. Saving with the display preference off preserves the prior per-card values. Thus hiding the UI neither clears the user's choices nor stops video transport, and the Source never becomes a second runtime truth store.

Because selector translation updates per-card truth before the host Source upsert completes, the bridge snapshots the complete Source/model-card state first. If the host upsert raises, it restores that state and the manager mirrors in memory. AstrBot may already have persisted the translated config before a later Provider reload fails, so the bridge calls an available host `save_config()` to persist the old snapshot as a compensating rollback, then best-effort reloads the old Source's model cards to repair a potentially partial runtime reload. The original host exception continues outward; persistence or old-instance reload failures remain notes on that primary error. This avoids falsely promising restoration of a layer whose compensation also failed.

Foreign Sources receive neither the persistent display field nor the temporary selector. A stale already-open 0.1.17 model dialog may still be translated at its save boundary for compatibility, but the generic model card is no longer a visible configuration entry point.

Fine-grained browser automation is presentation evidence, not capability or product-path authority. Coarse real Dashboard reachability remains a hard integration signal.

### Migration

Migration preserves configuration intent. It does not convert legacy fields into model facts. Current precedence is canonical per-card bool > exact-current-Source boolean retired 0.1.17 UI key > older per-card bool > legacy Source bool including `false` > historical `modalities: video`. Wrong-Source and foreign values are never promoted; all temporary/wrong-layer fields are removed after resolution, while `modalities` stays host-owned and unchanged. The full rule is documented in ADR-0004.

### Failure provenance

Local media/input transport failures use structured provenance (`AdapterInputTransportError`) to state that the model was not reached. The error object deliberately does not make routing/fallback recommendations.

### Testing and regression

- local contract tests judge plugin-owned invariants;
- AstrBot service tests judge host integration;
- raw-vs-plugin real Ark tests judge downstream protocol attribution;
- QQ product compatibility is judged only by a QQ-equivalent media path;
- full media revalidation is impact-triggered according to `docs/REGRESSION_SCOPE.md`.

## Rejected strategies

### Static model-ID capability completion

Rejected because legitimate counterexamples include third-party/open models, aliases, serving changes, and future model upgrades.

### Provider-wide video capability flag

Rejected because one Source can host multiple models with different behavior, and because a Source-wide flag polluted unrelated model cards and interfered with host fallback semantics.

The current Source-level `volcengine_video_controls_visible` field is not this rejected strategy: it has no runtime authority and only reveals or hides a per-model selector whose saved truth remains on each model card.

### Writing plugin dynamic feedback into global `LLM_METADATAS[model_id]`

Rejected because model IDs are not globally unique provider identities and stale data can cross Source/provider boundaries.

### Treating missing feedback as `false`

Rejected because missing feedback is not a negative capability observation and can hide the real cause of a failure.

### Building plugin-local fallback/routing

Rejected because AstrBot already owns the lifecycle and because duplicate routing systems can conflict.

### Making fine UI automation a release authority

Rejected because brittle browser assumptions can fail while the real host/service path remains healthy. UI structure remains useful evidence, but its claim scope is narrower.

### Broadening media code to satisfy non-equivalent raw fixtures

Rejected because a green direct-provider test can coexist with a broken QQ path. The product interface must not be silently redefined by the easiest test fixture.

## Validation philosophy

A correct implementation must survive both directions of review:

- **positive path:** legitimate supported behavior remains reachable;
- **counterexample path:** a local rule must not destroy another legitimate path.

The project therefore uses the layered evidence model in `docs/E2E_MATRIX.md`, the historical evidence index in `docs/TEST_HISTORY.md`, and the impact rules in `docs/REGRESSION_SCOPE.md`. The Source-page save contract has passed the AstrBot `4.26.1` and `4.27.2` service matrix at L3. A separate 2026-08-12 real AstrBot `4.27.2` Dashboard DOM run passed L4: owned Ark/Plan Sources each exposed exactly one master and one conditional selector scoped to their own 2/1 cards; close/reopen preserved selection without an API request; foreign exposed 0/0; all generic model dialogs exposed none of the canonical/retired/new video fields; `pageErrors=[]`. The goal is not to maximize test count; it is to make every conclusion traceable to an interface that can actually support that conclusion.
