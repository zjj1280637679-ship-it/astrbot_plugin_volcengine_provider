# Test Boundaries

## Plugin contract tests

Hard gate. These tests cover plugin-owned semantics:

- capability namespace and source/model-card ownership;
- migration precedence and preservation of explicit user intent, including exact-Source-only retired 0.1.17 UI promotion plus wrong-Source/foreign cleanup;
- current feedback normalization without stale persistence;
- audio/video payload construction;
- local transport error provenance;
- owned-Source selector projection, exact-card write-back, hidden-state preservation, and temporary Dashboard UI key removal.

They must not decide permanent model capability or duplicate AstrBot routing/fallback policy.

## AstrBot integration tests

Hard gate when the corresponding host API exists. These tests cover:

- provider registration;
- `ProviderConfigService` compatibility;
- source/model-card create/update/save boundaries;
- Source selector saves on both AstrBot 4.26.1 and 4.27.2, including that closing the display preference preserves per-card canonical values;
- host Source-upsert failure after selector translation restores the complete pre-call model-card list and re-raises the original failure;
- graceful degradation when optional Dashboard APIs are absent;
- supported AstrBot version matrix.

A host integration failure is not automatically an upstream/provider failure.

## Dashboard UI evidence

Non-blocking presentation evidence unless a coarse surface becomes unreachable.

Hard failures are limited to conditions such as:

- AstrBot cannot start;
- the plugin does not load;
- Dashboard authentication cannot complete in the known host path;
- the Provider page cannot be reached at all.

Layout details are collected rather than used as brittle CI assertions:

- screenshot;
- sanitized semantic DOM snapshot;
- visible text/labels;
- coarse layout counts;
- browser/page errors.

Provider-card layout screenshots must not be interpreted as model capability truth.

The current Source selector behavior is verified at L3 by the AstrBot 4.26.1/4.27.2 service matrix. A separate 2026-08-12 real AstrBot 4.27.2 Dashboard DOM run passed L4: Ark/Plan each showed one master and one selector restricted to their own 2/1 cards; close hid the selector, reopen preserved the selection with zero API requests; foreign showed 0/0; all Ark/Plan/foreign generic model dialogs omitted canonical, retired temporary, and new temporary video fields; `pageErrors=[]`. These observations remain presentation evidence only.

## Real Volcengine API tests

Runtime evidence. Use repository secrets and redact them from all logs/artifacts.

Test independently:

- ordinary Ark `/models` current response;
- ordinary text request;
- image request path where a test asset is available;
- audio request path where a test asset is available;
- video transport OFF (payload exclusion);
- video transport ON (payload inclusion and upstream response);
- tool-call path when suitable.

Record accepted/rejected/transport-failed separately. Never collapse every failure into `unsupported`.

## Complete user-path tests

Use only where the environment can faithfully reproduce the real chain. A complete path may include QQ/NapCat and therefore cannot be inferred from an Ark-only CI run.

## Skip rule

A skipped case must record the missing prerequisite. `skip` is not `pass`, and missing prerequisites are not negative capability facts.
