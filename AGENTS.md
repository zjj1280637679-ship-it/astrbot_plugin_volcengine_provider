# AI / Agent Project Entry Point

This file is the fastest safe entry point for an AI, coding agent, reviewer, or new maintainer.

## What this project is

This repository implements Volcengine Ark providers for AstrBot. It adapts Volcengine-specific protocols and media payloads to AstrBot's existing provider lifecycle. It does **not** own AstrBot routing, fallback, retry, or a second model-capability database.

## Read in this order

1. `docs/AI_RULES.md` — safe modification and ownership rules.
2. `docs/KNOWLEDGE_BOUNDARY.md` — why interaction, evidence, inference, and judgment are different layers.
3. `docs/RELEASE_BOUNDARY.md` — why the development repository and user runtime package are separate products.
4. `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` — concrete minimal-runtime packaging and marketplace rules.
5. `docs/AI_ONBOARDING.md` — project map and safe first actions.
6. `docs/PROJECT_STATE.json` — machine-readable current release state and validation frontier.
7. `docs/TEST_HISTORY.md` — important historical validations that must not disappear merely because they were not re-run.
8. `docs/REGRESSION_SCOPE.md` — change-to-test impact map and QQ-equivalent revalidation triggers.
9. `docs/DESIGN_DECISIONS.md` and `docs/ADR/` — objective conditions, rejected designs, and architectural reasons.
10. `docs/CAPABILITY_BOUNDARY.md` — adapter/model/system capability boundaries and feedback semantics.
11. `docs/E2E_MATRIX.md` — validation layers and product-path evidence.
12. `capabilities/SEMANTICS.json` — machine-readable capability/feedback contract.

## Non-negotiable ownership boundaries

- Adapter capability means “this plugin can express/transport a request shape”; it is not a claim that a model supports it.
- Runtime feedback is evidence from the current interaction, not permanent model truth.
- **Interaction is not judgment:** enough information to translate/send/display a request does not imply enough information or authority to make a global capability decision.
- Missing feedback is not `false`.
- Historical feedback must not override current feedback.
- A local media/input transport failure is not evidence that the model lacks the modality.
- A raw provider API success/failure is downstream protocol evidence; it is not by itself proof of the QQ/NapCat/AstrBot product path.
- The plugin must not recreate AstrBot routing, fallback, retry, provider lifecycle, or global model capability ownership.
- Provider-specific Dashboard fields must not leak into foreign providers.
- Migration preserves user intent/configuration, not model facts.
- **Development explainability is not runtime payload:** tests, CI, ADRs, AI onboarding, evidence, experiments, and internal research stay on the development branch unless a concrete runtime consumer requires them.
- The marketplace artifact is generated from an allow-list. Never publish the development repository archive as the user package.

## Before changing production code

Identify the affected layers before editing:

1. **product input path** — what real QQ/NapCat/AstrBot representation reaches the plugin;
2. **UI/config path** — what card/source exposes state and where it is saved;
3. **runtime path** — what provider/adapter actually sends to Ark or Agent Plan;
4. **feedback path** — what current upstream feedback is shown, and whether it is transient or persistent;
5. **historical evidence path** — which validated behavior becomes stale if this dependency changes;
6. **release path** — whether the change belongs in the generated `runtime` distribution or only in the development repository.

Then locate the corresponding regression test, `TEST_HISTORY`, `REGRESSION_SCOPE`, release manifest/rules, and ADR. If none exists for a new behavior, add the explanation before or with the behavior.

## Do not infer from names alone

Do not infer model capability from a model ID prefix, brand, vendor, historical result, or absence of a metadata icon. Volcengine is both a first-party platform for Doubao/Seed models and a cloud serving platform for third-party/open models, and model/platform behavior can change independently of this plugin.

## Current release work

The active release candidate is **0.1.17** on `release/0.1.17-runtime-package`.

0.1.17 does not expand provider functionality. It fixes the distribution boundary discovered by real AstrBot Store installation: the development repository had been packaged directly, allowing `.github/workflows/**` and other development material into the user ZIP. On Windows this caused extraction to fail partway through and left a partial plugin directory that then produced install-name conflicts.

The new target topology is:

`main (development + explainability + tests) -> allow-list build -> runtime branch (minimal user package)`.

`metadata.yaml.repo` is bound to the stable `runtime` branch, which AstrBot supports as a `/tree/{branch}` repository source. Runtime publication must prove the generated artifact itself loads on supported AstrBot versions before the marketplace-visible version is considered complete.

## AI intervention principle

These files are explanatory hooks, not runtime authority. They should make future AI intervention faster and safer by exposing assumptions, evidence, rejected paths, test entry points, historical validations, release boundaries, and the current decision frontier. They must not become a hidden control plane and must not be copied into the runtime distribution merely because they are useful to developers.