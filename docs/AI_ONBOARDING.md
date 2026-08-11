# AI Onboarding

## Purpose

This document lets an AI or new maintainer reconstruct the project quickly without treating historical conversation context, test output, or screenshots as hidden authority.

## Project map

| Area | Purpose | Start here |
|---|---|---|
| Engineering method | Epistemic pipeline, interface-existence rule, bounded iteration | `docs/ENGINEERING_METHODOLOGY.md` |
| Evidence semantics | What each kind of result can and cannot prove | `docs/EVIDENCE_LEVELS.md` |
| Test ownership | Which layer each test may judge | `docs/TEST_BOUNDARIES.md` |
| Provider runtime | AstrBot provider integration and Ark/Agent Plan calls | `providers.py`, `main.py` |
| Media adapters | Last-mile audio/video payload construction | `adapters/audio.py`, `adapters/video.py` |
| Input failure provenance | Distinguish local transport failure from upstream/model response | `adapters/errors.py` |
| Dynamic model feedback | Translate current Ark `/models` response for the current Source response only | `metadata/ark.py`, `capabilities/source_hints.py` |
| Agent Plan model listing | Agent Plan model-name discovery without model-ID capability priors | `metadata/agent_plan.py` |
| Model-card transport config | Per-card video request transport switch and migration | `capabilities/model_scope.py`, `capabilities/source_migration.py` |
| Dashboard bridge | Source-scoped model-card UI and save-boundary translation | `registry.py` |
| Machine semantics | Stable meanings for capability/feedback/config fields | `capabilities/SEMANTICS.json` |
| Persistent regressions | Current contract tests | `tests/test_*` |
| Product-path E2E | Host integration, UI evidence, real API matrix | `docs/E2E_MATRIX.md` |

## The four questions to answer before editing

1. **Objective condition:** What has actually been observed in AstrBot/Volcengine, rather than merely assumed?
2. **Expected outcome:** What user-visible or protocol-visible behavior is required?
3. **Current strategy:** Which layer currently owns that behavior, and why?
4. **Counterexample:** What legitimate path would break if this change generalized the current rule too far?

Then classify the strongest evidence available using `docs/EVIDENCE_LEVELS.md`.

## Current objective conditions

- Volcengine Ark can expose first-party Doubao/Seed models and third-party/open models through the same provider platform.
- Model capabilities and platform behavior change over time; static model-ID capability inference cannot be treated as permanent truth.
- AstrBot already owns provider lifecycle, fallback/retry behavior, provider-source/model-card management, metadata display, and Dashboard rendering.
- AstrBot capability icons are incomplete feedback surfaces, not a complete model capability truth table.
- Different AstrBot provider types use different Dashboard layouts and UI paths; code-equivalent configuration does not imply UI-equivalent reachability.
- Both plugin-owned Ark and Agent Plan providers currently register as AstrBot `chat_completion`; Agent Plan is not an `agent_runner` UI card.
- A model may support a modality while the complete QQ/NapCat/AstrBot/provider transport path is broken.
- The real AstrBot v4.27.2 Dashboard has already been built, started, logged into, and opened at the Provider page with this plugin loaded. That is UI/host evidence, not model-capability evidence.
- A previous provider-card Playwright matrix failed because its harness encoded unstable UI assumptions (welcome overlays, display labels, fixed source IDs, selector structure). Those failures did not implicate plugin runtime logic.

## Current expected outcome

- The plugin exposes the protocol ceiling it can transport: text/image/audio/video/tool-related request shapes where implemented.
- User/model-card configuration controls whether a transport path is attempted; it does not manufacture a model capability fact.
- Current upstream feedback may be displayed for the current response, but stale plugin feedback must not survive to defeat a newer response.
- Errors identify where a request failed without taking ownership of AstrBot's routing decision.
- Provider-specific configuration remains isolated from foreign providers.
- UI layout is collected as presentation evidence; it is not a brittle release gate unless the coarse Dashboard/Provider surface itself becomes unreachable.
- Real Volcengine API execution supplies the next runtime evidence layer.

## Current strategy

- Keep video transport configuration per model card and out of AstrBot `modalities`.
- Use Source-scoped temporary Dashboard keys only for UI rendering; translate/remove them at the save boundary.
- Keep ordinary Ark `/models` feedback transient, Source-scoped, single-use, and async-context isolated.
- Preserve explicit `false`, empty lists, integer `0`, and future unknown modality tokens when explicitly present in current feedback.
- Preserve legacy user intent during migration with precedence documented in ADR-0004.
- Treat contract/service tests as hard gates according to ownership.
- Treat Playwright as a coarse reachability check plus screenshot/semantic-DOM evidence collector, not as an authority on fine UI layout.
- Prefer AstrBot-native precedent and minimal existence experiments before constructing new automation around an assumed interface.

## Safe AI workflow

1. Read `AGENTS.md`, this document, `docs/ENGINEERING_METHODOLOGY.md`, `docs/EVIDENCE_LEVELS.md`, `docs/TEST_BOUNDARIES.md`, and relevant ADRs.
2. Inspect the current branch and tests before proposing abstractions.
3. For every arrow in a proposed flow, identify the concrete host/plugin/upstream interface that carries it. If unknown, run a minimal existence experiment first.
4. Search AstrBot-native precedent before inventing a plugin-side mechanism; use adjacent mature projects only when the host lacks precedent.
5. For a bug, record symptom -> failing layer -> preconditions -> what it proves -> what it does not prove -> whether it generalizes.
6. Construct at least one legitimate counterexample path and one non-regression path before broadening a rule.
7. Run the narrowest relevant test first, then the owning integration suite, then real E2E only when the evidence level requires it.
8. Record newly discovered objective conditions in `PROJECT_STATE.json` and the design docs when they materially change strategy.
9. Continue routine observe -> attribute -> minimally modify -> re-test -> record loops without repeated confirmation.

## Stop conditions

Stop and request a design decision only when a change would deliberately transfer ownership between AstrBot, this plugin, the user, and the upstream provider/model, or when two legitimate strategies have materially different product semantics. Routine implementation, testing, documentation synchronization, harness correction, and regression fixes should continue automatically.
