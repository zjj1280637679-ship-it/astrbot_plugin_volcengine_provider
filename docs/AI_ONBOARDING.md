# AI Onboarding

## Purpose

This document lets an AI or new maintainer reconstruct the project quickly without treating historical conversation context as hidden authority.

## Project map

| Area | Purpose | Start here |
|---|---|---|
| Provider runtime | AstrBot provider integration and Ark/Agent Plan calls | `providers.py`, `main.py` |
| Media adapters | Last-mile audio/video payload construction | `adapters/audio.py`, `adapters/video.py` |
| Input failure provenance | Distinguish local transport failure from upstream/model response | `adapters/errors.py` |
| Dynamic model feedback | Translate current Ark `/models` response for the current Source response only | `metadata/ark.py`, `capabilities/source_hints.py` |
| Agent Plan model listing | Agent Plan model-name discovery without model-ID capability priors | `metadata/agent_plan.py` |
| Model-card transport config | Per-card video request transport switch and migration | `capabilities/model_scope.py`, `capabilities/source_migration.py` |
| Dashboard bridge | Source-scoped model-card UI and save-boundary translation | `registry.py` |
| Machine semantics | Stable meanings for capability/feedback/config fields | `capabilities/SEMANTICS.json` |
| Persistent regressions | Current contract tests | `tests/test_*` |
| Product-path E2E | Planned/active provider-card + UI + real API matrix | `docs/E2E_MATRIX.md` |

## The four questions to answer before editing

1. **Objective condition:** What has actually been observed in AstrBot/Volcengine, rather than merely assumed?
2. **Expected outcome:** What user-visible or protocol-visible behavior is required?
3. **Current strategy:** Which layer currently owns that behavior, and why?
4. **Counterexample:** What legitimate path would break if this change generalized the current rule too far?

## Current objective conditions

- Volcengine Ark can expose first-party Doubao/Seed models and third-party/open models through the same provider platform.
- Model capabilities and platform behavior change over time; static model-ID capability inference cannot be treated as permanent truth.
- AstrBot already owns provider lifecycle, fallback/retry behavior, provider-source/model-card management, metadata display, and Dashboard rendering.
- AstrBot capability icons are incomplete feedback surfaces, not a complete model capability truth table.
- Different AstrBot provider types use different Dashboard layouts and UI paths; code-equivalent configuration does not imply UI-equivalent reachability.
- A model may support a modality while the complete QQ/NapCat/AstrBot/provider transport path is broken.

## Current expected outcome

- The plugin exposes the protocol ceiling it can transport: text/image/audio/video/tool-related request shapes where implemented.
- User/model-card configuration controls whether a transport path is attempted; it does not manufacture a model capability fact.
- Current upstream feedback may be displayed for the current response, but stale plugin feedback must not survive to defeat a newer response.
- Errors should identify where a request failed without taking ownership of AstrBot's routing decision.
- Every legitimate provider-card UI path should be reachable and visually scoped correctly.

## Current strategy

- Keep video transport configuration per model card and out of AstrBot `modalities`.
- Use Source-scoped temporary Dashboard keys only for UI rendering; translate/remove them at the save boundary.
- Keep ordinary Ark `/models` feedback transient, Source-scoped, single-use, and async-context isolated.
- Preserve explicit `false`, empty lists, integer `0`, and future unknown modality tokens when explicitly present in current feedback.
- Preserve legacy user intent during migration with precedence documented in ADR-0004.
- Validate the release with both code contracts and a real API × provider-card × UI-layout E2E matrix.

## Safe AI workflow

1. Read `AGENTS.md`, this document, and relevant ADRs.
2. Inspect the current branch and tests before proposing new abstractions.
3. Prefer finding an AstrBot-native mechanism before adding a plugin-side mechanism.
4. For a bug, construct at least one legitimate counterexample path and one non-regression path.
5. Run the narrowest relevant test first, then the full boundary suite, then real E2E when runtime behavior is touched.
6. Record newly discovered objective conditions in the design docs if they materially change the strategy.

## Stop conditions

Stop and ask for a design decision when a change would deliberately transfer ownership between AstrBot, this plugin, the user, and the upstream provider/model. Routine implementation, testing, documentation synchronization, and regression fixes should continue without repeated confirmation.