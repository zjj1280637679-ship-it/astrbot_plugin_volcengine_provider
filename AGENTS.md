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

The active release candidate is **0.1.18** on the current release PR branch. Its Source-video UI, migration, and transactional-save behavior are implemented and validated, but the stable `runtime` branch must still be regenerated and revalidated after merge before publication is complete.

0.1.18 moves the visible per-model video configuration surface out of the shared generic model card and into each owned Ark / Agent Plan Provider Source. The persistent Source switch only shows or hides the exact-Source selector; the canonical per-card transport value remains `volcengine_video_input_enabled`, hidden selections remain active, foreign Sources receive no field, and a failed host Source upsert restores the complete pre-call model-card state. Migration deliberately preserves the historical 0.1.17 exact-Source UI residue only when its encoded Source identity matches the card.

0.1.17 established the distribution boundary after a real AstrBot Store installation exposed development files such as `.github/workflows/**` in the user ZIP. That historical release separated development state from the minimal user package and remains the basis for 0.1.18 publication.

The publication topology is:

`main -> all-PR/main-push gate -> exact allow-list artifact -> unique candidate -> 4-cell native installer gate -> leased runtime promotion -> blocking 4-cell runtime recheck`.

`metadata.yaml.repo` is bound to the stable `runtime` branch, which AstrBot supports as a `/tree/{branch}` repository source. For 0.1.18, merge and metadata changes alone are not publication proof: the regenerated artifact must load on supported AstrBot versions, the actual runtime branch/archive must report 0.1.18, and the native installer paths must pass before the marketplace-visible version is considered complete.

## AI intervention principle

These files are explanatory hooks, not runtime authority. They should make future AI intervention faster and safer by exposing assumptions, evidence, rejected paths, test entry points, historical validations, release boundaries, and the current decision frontier. They must not become a hidden control plane and must not be copied into the runtime distribution merely because they are useful to developers.
