# Test Boundaries

## Plugin contract tests

Hard gate. These tests cover plugin-owned semantics:

- capability namespace and source/model-card ownership;
- migration precedence and preservation of explicit user intent;
- current feedback normalization without stale persistence;
- audio/video payload construction;
- local transport error provenance;
- temporary Dashboard UI key translation/removal.

They must not decide permanent model capability or duplicate AstrBot routing/fallback policy.

## AstrBot integration tests

Hard gate when the corresponding host API exists. These tests cover:

- provider registration;
- `ProviderConfigService` compatibility;
- source/model-card create/update/save boundaries;
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
