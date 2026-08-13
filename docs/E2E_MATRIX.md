# Provider × Host × Product Evidence Matrix

Lifecycle role: **WARM/HISTORICAL evidence ledger**. This document defines claim scope and records observed evidence. It does **not** define the current release goal/frontier; read `docs/PROJECT_STATE.json` for HOT state.

## Purpose

Separate code correctness, AstrBot integration, Dashboard presentation, downstream Ark protocol behavior, and QQ product compatibility. A green lower-layer test must not be promoted into a stronger claim than its interface supports, and a harness/teardown failure must not overwrite a product step that already passed.

## Evidence layers

### L2 — local contract/regression

Validates plugin-owned invariants such as migration precedence, foreign-provider isolation, model-field normalization, transient feedback semantics, failure provenance, and trusted media behavior.

Cannot prove AstrBot runtime integration or QQ compatibility.

### L3 — real AstrBot service/runtime integration

Validates supported host APIs and packaged runtime behavior, including Provider registration, ProviderConfigService create/update/save boundaries, Source save translation, request override hooks, and host-version compatibility.

Proves host integration, not model capability.

### L4 — real Dashboard reachability and presentation evidence

Validates that a real AstrBot Dashboard builds/starts, login succeeds, Provider UI is reachable, and the observed DOM/controls match the presentation claim being tested.

Presentation evidence includes screenshots, semantic DOM/visible text, save/reopen persistence, and page errors. It does not become model-capability truth.

#### 0.1.18 historical Source-video UI evidence

On 2026-08-12, real AstrBot 4.27.2 Dashboard observation showed:

- Ark and Agent Plan each had exactly one Source video master;
- opened selectors contained only that Source's 2 / 1 model cards;
- close hid the selector and reopen preserved selection with zero API requests;
- foreign Source had 0 masters / 0 selectors;
- generic Ark/Plan/foreign model dialogs contained none of the canonical/retired/new Source-video transport fields;
- `pageErrors=[]`.

This remains historical evidence for the released 0.1.18 Source UI contract.

#### 0.1.19 candidate model-field evidence

Run `31621942332` executed a real AstrBot 4.27.2 Dashboard against the 0.1.19 candidate. The browser matrix itself returned `all_passed=true` with `page_errors=[]`:

- saved Ark and Agent Plan model dialogs exposed the bilingual Volcengine horizontal fields;
- Video=Compressed, Thinking=Auto, Effort=High, Temperature, Top P, Max Output Tokens, Frequency Penalty, and Presence Penalty survived save/reopen;
- the released 0.1.18 Source master/selector remained intact after model-field save;
- foreign OpenAI model dialogs exposed no Volcengine fields;
- the evidence artifact uploaded successfully.

The overall GitHub job later ended red **only in `Post Run astral-sh/setup-uv@v6`**: a background `uv -> astrbot` process still held the setup-uv cache lock, `uv cache prune --ci` waited 300 seconds and timed out. This is workflow teardown evidence, not a UI-rendering failure. The HOT state tracks the cleanup action.

### L5 — downstream Volcengine protocol attribution

Where a real credential and meaningful fixture exist, compare a minimal raw upstream request with the same logical path through the plugin.

```text
raw success + plugin success
  -> downstream protocol and plugin path both worked under observed conditions

raw success + plugin failure
  -> plugin path is suspect

raw failure + plugin failure
  -> upstream/account/model/test-condition boundary remains plausible
```

L5 is not automatically QQ product compatibility.

### L6 — QQ-equivalent product path

For QQ media features:

```text
QQ event
  -> NapCat / OneBot
  -> AstrBot event/media lifecycle
  -> MediaResolver
  -> plugin audio/video last mile
  -> Ark request
  -> provider/model response
```

This is the layer that can validate QQ-oriented audio/video compatibility. A generated WAV/MP4 sent directly to a Provider is not equivalent.

## Stable provider identities

The plugin-owned providers register as AstrBot `chat_completion` providers:

- `volcengine_ark_chat_completion`;
- `volcengine_agent_plan_chat_completion`.

Agent Plan is not an `agent_runner` card.

## Stable required invariants

### Capability / feedback

- no static model-ID capability oracle;
- missing feedback remains unknown;
- explicit current `false`, empty list, and `0` remain observations when upstream returned them;
- future/unknown modality tokens are not deleted solely because today's plugin cannot interpret them;
- transient Ark feedback does not become permanent global `LLM_METADATAS[model_id]` truth.

### Dashboard / config isolation

For the 0.1.20 model-dialog video option:

- only the private dialog schema clone selected for Ark/Agent Plan receives the additional `video` option;
- foreign provider dialogs retain the host's original `modalities` options and hide Volcengine request rows;
- owned save/reopen keeps `modalities: video` and the compatibility runtime Boolean aligned;
- the AstrBot Dashboard asset on disk remains unchanged, and an unknown/ambiguous asset skips only the optional UI rather than blocking Provider registration.

For the historical 0.1.18 Source UI:

- the shared top capability row is not extended globally for Volcengine video;
- owned Sources receive the Source-specific presentation workflow;
- hiding the Source selector preserves per-card video state;
- foreign Sources do not receive Volcengine Source-video fields.

For 0.1.19 ordinary saved-model body fields:

- only owned Ark/Agent Plan model copies receive the Volcengine horizontal keys;
- foreign model copies are stripped of Volcengine 0.1.19 keys;
- request settings remain distinct from AstrBot `modalities`;
- empty optional values mean no injection rather than zero;
- explicit horizontal settings outrank the same `custom_extra_body` request keys.

### Migration

Historical 0.1.18 video migration precedence remains an owned compatibility constraint: canonical per-card state outranks exact matching retired UI residue, older per-card state, legacy Source state, and finally historical `modalities: video` as a migration clue. Wrong-Source/foreign debris is never promoted and `modalities` remains host-owned.

### Failure provenance

- local media/input transport failure means the model was not reached;
- upstream rejection remains upstream evidence;
- browser/test-harness failure remains harness evidence;
- workflow post-cleanup/cache failure remains teardown evidence unless it prevented the product evidence from running;
- the plugin does not add model switching/fallback decisions.

## Historical media regression assets

QQ-oriented audio/video validations are indexed in `docs/TEST_HISTORY.md`. Rerun requirements are decided by `docs/REGRESSION_SCOPE.md`, not by release number alone.

## Evidence summary format

```text
Plugin contracts
  owned invariants                         PASS/FAIL
  foreign-provider isolation              PASS/FAIL
  failure provenance                      PASS/FAIL

AstrBot integration
  4.26.1 declared-minimum integration     PASS/FAIL
  4.27.2 integration                      PASS/FAIL
  Dashboard product/presentation steps    PASS/FAIL
  workflow teardown                       PASS/FAIL (separate verdict)

Downstream attribution
  ordinary Ark /models                    PASS/FAIL/SKIP(reason)
  ordinary Ark text/image/media           PASS/FAIL/SKIP(reason)

QQ product regressions
  audio                                   HISTORICAL_VALID / REVALIDATED / STALE(reason)
  video                                   HISTORICAL_VALID / REVALIDATED / STALE(reason)
```

A `SKIP` must include a reason. Historical evidence must not be silently upgraded to current truth, but it also must not be silently erased.
