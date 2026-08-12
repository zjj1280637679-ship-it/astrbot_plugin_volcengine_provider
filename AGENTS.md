# AI / Agent Project Entry Point

Lifecycle role: **WARM entry point**. This file provides stable ownership and navigation rules only.

**HOT/current state authority: `docs/PROJECT_STATE.json`.** Do not reconstruct the current release goal, blocker, or validation frontier from this file, README, CHANGELOG, old PR text, or historical test output. Read `docs/KNOWLEDGE_LIFECYCLE.md` for HOT/WARM/COLD rules.

## What this project is

This repository implements Volcengine Ark providers for AstrBot. It adapts Volcengine-specific protocols and media payloads to AstrBot's existing provider lifecycle. It does **not** own AstrBot routing, fallback, retry, or a second model-capability database.

## Read in this order

1. `docs/PROJECT_STATE.json` — current version, goal, strategy, blockers/frontier.
2. `docs/KNOWLEDGE_LIFECYCLE.md` — HOT/WARM/COLD demotion, invalidators, superseded/rejected rules.
3. `docs/AI_RULES.md` — safe modification and ownership rules.
4. `docs/KNOWLEDGE_BOUNDARY.md` — interaction/evidence/judgment boundary.
5. `docs/RELEASE_BOUNDARY.md` — development repository versus user runtime package.
6. `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` — minimal-runtime packaging/marketplace rules.
7. `docs/AI_ONBOARDING.md` — project map and safe workflow.
8. `docs/TEST_HISTORY.md` — historical validations that remain evidence within their premises.
9. `docs/REGRESSION_SCOPE.md` — when historical evidence becomes stale and must be rerun.
10. `docs/DESIGN_DECISIONS.md` and `docs/ADR/` — stable constraints and rejected strategies.
11. `docs/CAPABILITY_BOUNDARY.md` — adapter/model/system capability boundaries.
12. `docs/E2E_MATRIX.md` — validation layers and evidence ledger.
13. `capabilities/SEMANTICS.json` — machine-readable capability/feedback semantics.

## Non-negotiable ownership boundaries

- Adapter capability means “this plugin can express/transport a request shape”; it is not a claim that a model supports it.
- Runtime feedback is scoped evidence, not permanent model truth.
- Interaction is not judgment: receiving/translating/sending/displaying information does not grant authority for a global capability verdict.
- Missing feedback is not `false`.
- Historical feedback must not override current feedback.
- A local media/input transport failure is not evidence that the model lacks the modality.
- A raw provider API result is downstream protocol evidence; it is not by itself proof of the QQ/NapCat/AstrBot product path.
- The plugin must not recreate AstrBot routing, fallback, retry, provider lifecycle, or global model capability ownership.
- Provider-specific Dashboard fields must not leak into foreign providers.
- Migration preserves user intent/configuration, not model facts.
- Development explainability is not runtime payload: tests, CI, ADRs, evidence, experiments, internal research, and lifecycle documents stay outside the generated runtime artifact unless a concrete runtime consumer requires them.
- The marketplace artifact is generated from an allow-list. Never publish the development repository archive as the user package.

## Dashboard scope rule

Do not overgeneralize the 0.1.18 Source-UI decision.

- The shared **top capability/modalities** surface is not a reliable provider-specific extension boundary for the fifth video capability checkbox/icon.
- Ordinary **saved-model edit-body rows** can be provider-specific when the owned Source/model identity is known and the fields are projected only onto owned model copies.

ADR-0003 governs the first problem; ADR-0005 records the scope correction and knowledge-lifecycle rule.

## Before changing production code

Identify the affected layers:

1. product input path;
2. UI/config path;
3. runtime request path;
4. feedback path;
5. historical evidence path;
6. release/distribution path;
7. knowledge lifecycle: is the requirement/strategy HOT, WARM, COLD, superseded, rejected, or invalidated?

Then locate the corresponding regression test, `TEST_HISTORY`, `REGRESSION_SCOPE`, release rules, and ADR. If the behavior is new, add the smallest explanation that should survive the current release.

## Do not infer from names alone

Do not infer model capability from a model ID prefix, brand, vendor, historical result, or absence of a metadata icon. Volcengine is both a first-party platform for Doubao/Seed models and a serving platform for third-party/open models, and model/platform behavior can change independently.

## Release/history lookup

Do **not** maintain release state here. Use:

- current/HOT: `docs/PROJECT_STATE.json`;
- published/historical validation: `docs/TEST_HISTORY.md` and `CHANGELOG.md`;
- completed state snapshots: `docs/archive/`.

This separation is intentional: old release facts stay searchable without remaining action-driving.

## AI intervention principle

Project documentation is an explanatory layer, not runtime authority. It should expose assumptions, evidence, rejected paths, test entry points, invalidators, and current decision frontier while preventing historical goals from silently becoming current instructions.
