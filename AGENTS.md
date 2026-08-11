# AI / Agent Project Entry Point

This file is the fastest safe entry point for an AI, coding agent, reviewer, or new maintainer.

## What this project is

This repository implements Volcengine Ark providers for AstrBot. It adapts Volcengine-specific protocols and media payloads to AstrBot's existing provider lifecycle. It does **not** own AstrBot routing, fallback, retry, or a second model-capability database.

## Read in this order

1. `docs/AI_ONBOARDING.md` — current project map and safe first actions.
2. `docs/DESIGN_DECISIONS.md` — objective conditions discovered during development, target outcomes, and current strategy.
3. `docs/CAPABILITY_BOUNDARY.md` — adapter/model/system capability boundaries and feedback semantics.
4. `docs/ADR/` — why rejected designs were rejected.
5. `docs/E2E_MATRIX.md` — product-path validation matrix, including UI layout and real Volcengine API paths.
6. `capabilities/SEMANTICS.json` — machine-readable capability/feedback contract.
7. `docs/PROJECT_STATE.json` — machine-readable current state and active validation target.

## Non-negotiable ownership boundaries

- Adapter capability means “this plugin can express/transport a request shape”; it is not a claim that a model supports it.
- Runtime feedback is evidence from the current interaction, not permanent model truth.
- Missing feedback is not `false`.
- Historical feedback must not override current feedback.
- A local media/input transport failure is not evidence that the model lacks the modality.
- The plugin must not recreate AstrBot routing, fallback, retry, provider lifecycle, or global model capability ownership.
- Provider-specific Dashboard fields must not leak into foreign providers.
- Migration preserves user intent/configuration, not model facts.

## Before changing production code

Identify all three layers affected by the change:

1. **UI/config path** — what card/source layout exposes the state and where it is saved.
2. **runtime path** — what provider/adapter actually sends to Ark or Agent Plan.
3. **feedback path** — what current upstream feedback is shown, and whether it is transient or persistent.

Then locate the corresponding regression test and ADR. If none exists for a new behavior, add the explanation before or with the behavior.

## Do not infer from names alone

Do not infer model capability from a model ID prefix, brand, vendor, historical result, or absence of a metadata icon. Volcengine is both a first-party platform for Doubao/Seed models and a cloud serving platform for third-party/open models, and model/platform behavior can change independently of this plugin.

## Current release work

The active branch `refactor/0.1.15-feedback-boundary` is validating 0.1.15. The next validation layer is a **real Volcengine API × provider-card path × Dashboard UI-layout matrix E2E**. This exists because code-level correctness alone does not prove that a user can reach every legitimate path through AstrBot's different provider-card layouts.

## AI intervention principle

These files are explanatory hooks, not runtime authority. They should make future AI intervention faster and safer by exposing assumptions, evidence, rejected paths, test entry points, and the current decision frontier. They must not become a hidden control plane that changes provider behavior.