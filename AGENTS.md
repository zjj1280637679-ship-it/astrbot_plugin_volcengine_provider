# AI / Agent Project Entry Point

Lifecycle role: **WARM entry point**. This file provides stable ownership and navigation rules only.

**HOT/current state authority: `docs/PROJECT_STATE.json`.** Read its `verdict` first. If `active_release_candidate` is `null`, no branch, PR, local package, green sub-job, or historical workflow is a release candidate. Do not reconstruct the current release goal from README, CHANGELOG, PR text, branch names, or isolated test output.

## What this project is

This repository implements Volcengine Ark providers for AstrBot. It adapts Volcengine-specific protocols and media payloads to AstrBot's existing provider lifecycle. It does **not** own AstrBot routing, fallback, retry, or a second model-capability database.

## Branch discipline: one installation truth

`main` is both the default development branch and AstrBot's installation source. The old `runtime` branch is retained only as historical recovery evidence and must never receive new releases. A patch version is published by merging one reviewed, fully installable tree into `main` with a strictly newer `metadata.yaml` version. Temporary review branches are allowed; permanent version-named, runtime-candidate, or rollback trees are not.

## Read in this order

1. `docs/PROJECT_STATE.json` — current verdict, stable release, active candidate, frontier, and stopped experiments.
2. **For any model-card / Video / modalities / Provider Source UI task, read `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md` before changing code.** This is the non-negotiable product boundary recovered in 0.1.22.
3. `docs/AI_ONBOARDING.md` — choose the one subsystem relevant to the task.
4. `docs/AI_RULES.md` and `docs/KNOWLEDGE_LIFECYCLE.md` — modification and lifecycle rules.
5. Only then read the specific ADR, test, release rule, or runtime module linked by the project map.

Do not bulk-read every historical document before identifying the affected object. More context is not automatically more authority.

## Status and evidence identity

- **Stable release**, **active candidate**, **external observation**, and **experiment** are different objects. Never combine their pass/fail receipts into one verdict.
- A feature branch is an experiment unless `PROJECT_STATE.verdict.active_release_candidate` explicitly names it as a `validating` candidate. A validating candidate remains `releaseable: false`; it may become `ready` only after every blocking acceptance condition passes, and must not merge, tag, or publish before that transition.
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
- Development files may coexist in the default repository, but production modules must never import tests, evidence, governance, or lifecycle documents. Secrets, private configuration, cache files, and local artifacts never belong in the repository.
- AstrBot and the official Collection validator clone the default repository branch. Before publication, prove that the `main` root itself contains the complete runtime closure; never hide required code in a second generated branch.

## Dashboard scope rule — recovered 0.1.22 invariant

Do **not** confuse the Provider Source page with one configured model card.

The recovered product requirement is exact:

- the native `Video` / `视频` option belongs beside Text, Image, Audio, and Tool use in the **single model card's native `modalities` checklist**;
- it appears only after the Dashboard has selected an owned Volcengine Ark or Agent Plan Source and cloned the shared schema into that model dialog's **private schema copy**;
- it must not appear in OpenAI, xAI, Gemini, or any other foreign Provider model card;
- it must not be replaced by a Provider Source master switch, Source-page model selector, custom request field, explanatory row, hidden value, or create-only decoration;
- the saved `modalities` membership is the current model-card UI truth and must survive save/reopen;
- request-time video conversion must follow that current card value;
- unload/release must restore the host UI/service boundary without a fifth global modality residue.

A **backend-only mutation of the shared `provider.items.modalities` schema is forbidden**. At that layer a plugin cannot safely express “only these two selected Source types” without risking global leakage. The known-good implementation therefore adapts the model dialog after its private clone has access to `selectedProviderSource.type`.

The historical 0.1.20 branch is useful evidence, but its old final verdict must not override the recovered 0.1.22 result: the correct source-scoped native Video implementation was recovered, validated, and merged under the 0.1.22 identity. The permanent acceptance definition is `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`, not an obsolete requirement for retired Source controls or `_volcengine_video_input_mode_ui`.

## Before changing production code

Identify the affected layers:

1. product input path;
2. UI/config path;
3. runtime request path;
4. feedback path;
5. historical evidence path;
6. release/distribution path;
7. knowledge lifecycle: is the requirement/strategy HOT, WARM, COLD, superseded, rejected, or invalidated?

Then locate the corresponding regression test, `TEST_HISTORY`, `REGRESSION_SCOPE`, release rules, ADR, and—when Video/model-card scope is involved—the five-condition joint gate in `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`. If the behavior is new, add the smallest explanation that should survive the current release.

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
