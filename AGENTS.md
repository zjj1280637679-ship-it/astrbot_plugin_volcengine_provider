# AI / Agent Project Entry Point

Lifecycle role: **WARM entry point**. This file provides stable ownership and navigation rules only.

**HOT/current state authority: `docs/PROJECT_STATE.json`.** Read its `verdict` first. If `active_release_candidate` is `null`, no branch, PR, local package, green sub-job, or historical workflow is a release candidate. Do not reconstruct the current release goal from README, CHANGELOG, PR text, branch names, or isolated test output.

## What this project is

This repository implements Volcengine Ark providers for AstrBot. It adapts Volcengine-specific protocols and media payloads to AstrBot's existing provider lifecycle. It does **not** own AstrBot routing, fallback, retry, or a second model-capability database.

## Read in this order

1. `docs/PROJECT_STATE.json` — current verdict, stable release, active candidate, frontier, and stopped experiments.
2. `docs/AI_ONBOARDING.md` — choose the one subsystem relevant to the task.
3. `docs/AI_RULES.md` and `docs/KNOWLEDGE_LIFECYCLE.md` — modification and lifecycle rules.
4. Only then read the specific ADR, test, release rule, or runtime module linked by the project map.

Do not bulk-read every historical document before identifying the affected object. More context is not automatically more authority.

## Status and evidence identity

- **Stable release**, **active candidate**, **external observation**, and **experiment** are different objects. Never combine their pass/fail receipts into one verdict.
- A feature branch remains an experiment until every blocking acceptance condition passes and `PROJECT_STATE.verdict.active_release_candidate` names it explicitly.
- A workflow file has one evidence identity. A new experiment must add a clearly named `EXPERIMENT` workflow; it must not repurpose a stable workflow and inherit its historical name.
- A green runtime-load job proves loading only. A green create-dialog check does not prove save/reopen persistence. A GitHub release result does not prove marketplace refresh.
- Stopped experiments move to `docs/archive/` and remain non-action-driving unless their recorded resume condition is satisfied.

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
- The closed 0.1.20 private-dialog-clone experiment achieved create-dialog isolation but failed save/reopen completeness. It is archived evidence, not a current solution.

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
