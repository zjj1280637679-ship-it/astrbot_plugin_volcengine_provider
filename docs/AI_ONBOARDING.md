# AI Onboarding

## Purpose

This document lets an AI or new maintainer reconstruct the project quickly without treating historical conversation context, test output, screenshots, or one successful interaction as hidden authority.

## Project map

| Area | Purpose | Start here |
|---|---|---|
| AI modification rules | Ownership and safe-edit boundaries | `docs/AI_RULES.md` |
| Knowledge boundary | Interaction vs evidence vs judgment | `docs/KNOWLEDGE_BOUNDARY.md` |
| Engineering method | Epistemic pipeline, interface-existence rule, bounded iteration | `docs/ENGINEERING_METHODOLOGY.md` |
| Evidence semantics | What each kind of result can and cannot prove | `docs/EVIDENCE_LEVELS.md` |
| Test ownership | Which layer each test may judge | `docs/TEST_BOUNDARIES.md` |
| Historical validation | Important successful paths and what they proved | `docs/TEST_HISTORY.md` |
| Regression impact | When a full QQ-equivalent media rerun is required | `docs/REGRESSION_SCOPE.md` |
| Provider runtime | AstrBot provider integration and Ark/Agent Plan calls | `providers.py`, `main.py` |
| Media adapters | Last-mile audio/video payload construction | `adapters/audio.py`, `adapters/video.py` |
| Input failure provenance | Distinguish local transport failure from upstream/model response | `adapters/errors.py` |
| Dynamic model feedback | Translate current Ark `/models` response for the current Source response only | `metadata/ark.py`, `capabilities/source_hints.py` |
| Agent Plan model listing | Agent Plan model-name discovery without model-ID capability priors | `metadata/agent_plan.py` |
| Model-card transport config | Per-card video request transport switch and migration | `capabilities/model_scope.py`, `capabilities/source_migration.py` |
| Dashboard bridge | Source-scoped model-card UI and save-boundary translation | `registry.py` |
| Machine semantics | Stable meanings for capability/feedback/config fields | `capabilities/SEMANTICS.json` |
| Persistent regressions | Current contract tests | `tests/test_*` |
| Product-path evidence | Host integration, UI evidence, real API attribution | `docs/E2E_MATRIX.md` |
| Runtime distribution and publication | Development/runtime boundary, package allow-list, promotion safety, and external validation frontier | `docs/RELEASE_BOUNDARY.md`, `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md`, `docs/PROJECT_STATE.json` |

## The five questions to answer before editing

1. **Objective condition:** What has actually been observed rather than assumed?
2. **Expected outcome:** What user-visible or protocol-visible behavior is required?
3. **Current owner:** Which layer owns that behavior: QQ/NapCat, AstrBot, this adapter, the user, or upstream?
4. **Counterexample:** What legitimate path would break if this rule generalized too far?
5. **Regression edge:** Which historical evidence becomes stale if this dependency changes?

Then classify the strongest evidence available using `docs/EVIDENCE_LEVELS.md`.

## Current objective conditions

- Volcengine Ark can expose first-party Doubao/Seed models and third-party/open models through the same provider platform.
- Model capabilities and platform behavior change over time; static model-ID capability inference cannot be treated as permanent truth.
- AstrBot already owns provider lifecycle, fallback/retry behavior, provider-source/model-card management, metadata display, and Dashboard rendering.
- AstrBot capability icons are incomplete feedback surfaces, not a complete model-capability truth table.
- Different AstrBot provider types can use different Dashboard layouts and UI paths; UI automation must prove the interface it is driving instead of guessing structure.
- Both plugin-owned Ark and Agent Plan providers currently register as AstrBot `chat_completion`; Agent Plan is not an `agent_runner` UI card.
- A model may support a modality while the complete QQ/NapCat/AstrBot/provider transport path is broken, and the inverse test mismatch is also possible: a synthetic raw fixture may fail while an unchanged QQ-oriented path remains valid under its original conditions.
- The real AstrBot v4.27.2 Dashboard has been built, started, logged into, and opened at the Provider page with this plugin loaded. That is UI/host evidence, not model-capability evidence.
- Fine Playwright provider-card automation encoded unstable harness assumptions and was retired as a release gate; coarse reachability plus evidence collection remains useful.
- Historical QQ-oriented media validation is tracked explicitly and must be re-run based on dependency impact, not because every release must reproduce every old E2E.

## Current expected outcome

- The plugin exposes the protocol ceiling it can transport without converting transport support into permanent model capability claims.
- User/model-card configuration controls whether a transport path is attempted; it does not manufacture a model capability fact.
- Current upstream feedback may be displayed for the current response, but stale plugin feedback must not survive to defeat a newer response.
- Errors identify where a request failed without taking ownership of AstrBot's routing decision.
- Provider-specific configuration remains isolated from foreign providers.
- Raw upstream tests are used for downstream protocol attribution, while QQ compatibility is judged only by a QQ-equivalent media path.
- Historical successful paths remain evidence until an impact edge invalidates their conditions.

## Current strategy

- Keep video transport configuration per model card and out of AstrBot `modalities`.
- Use Source-scoped temporary Dashboard keys only for UI rendering; translate/remove them at the save boundary.
- Keep ordinary Ark `/models` feedback transient, Source-scoped, single-use, and async-context isolated.
- Preserve explicit `false`, empty lists, integer `0`, and future unknown modality tokens when explicitly present in current feedback.
- Preserve legacy user intent during migration with precedence documented in ADR-0004.
- Treat contract/service tests as hard gates according to ownership.
- Treat Playwright as coarse reachability plus presentation evidence, not as an authority on fine UI layout.
- Prefer AstrBot-native precedent and minimal existence experiments before constructing new automation around an assumed interface.
- Use `TEST_HISTORY` + `REGRESSION_SCOPE` before deciding whether audio/video needs a full QQ-equivalent rerun.
- Never broaden media production code merely to make a non-equivalent raw fixture pass.

## Current release state

`0.1.17` is released at the repository/runtime-distribution layer. `main` remains the development state; the minimal user package is published from `runtime`. It is not an active release candidate, and historical release branch names must not be used to infer current status.

0.1.17 preserves the 0.1.16 Provider, media, capability-feedback, migration, and AstrBot fallback/retry semantics. Its release change is the development/runtime boundary: the store package is generated from an explicit allow-list instead of shipping the development repository archive.

Publication safety is part of the release contract. The main gate covers all pull requests targeting `main` and all `main` pushes, and publication is serialized. The generated runtime tree is compared with `runtime` first; an identical tree is a no-op that skips both validation matrices and promotion. When content changes, the run creates one unique temporary candidate branch and explicitly calls the reusable AstrBot `4.26.1` / `4.27.2` × `repo_branch` / `download_url` validator before promotion. Immediately before promotion it re-reads `origin/main`, then updates `runtime` with an exact old-SHA `force-with-lease`. Git has no read-only compare-and-swap for an unchanged `main` ref, so these are deliberately not described as one atomic transaction: a main push in the final update interval receives its own subsequent gate/publisher, while publication serialization and the runtime lease prevent it from being overwritten by a concurrent publisher. After a real promotion, the same publish run explicitly calls the same reusable four-cell validator against the promoted `runtime`; this post-publish check is a blocking publication job.

Current ordinary Ark `/models`, text, and image raw-vs-plugin checks remain downstream L5 attribution evidence. Current Agent Plan checks with an ordinary-Ark credential fail in both raw and plugin paths at the same authentication/account boundary and therefore do not justify a production-code change. Audio/video product compatibility is not redefined by those raw probes; see `TEST_HISTORY` and `REGRESSION_SCOPE`.

The remaining external frontier is to observe the AstrBot Store showing `0.1.17`, resolving its install source to `runtime`, and completing a real Windows Store installation without development files or partial-install conflicts.

## Safe AI workflow

1. Read `AGENTS.md`, `AI_RULES`, `KNOWLEDGE_BOUNDARY`, this document, `ENGINEERING_METHODOLOGY`, `EVIDENCE_LEVELS`, `TEST_BOUNDARIES`, `TEST_HISTORY`, `REGRESSION_SCOPE`, and the relevant ADR.
2. Inspect the current branch and changed-file impact before proposing abstractions.
3. For every arrow in a proposed flow, identify the concrete host/plugin/upstream interface that carries it. If unknown, run a minimal existence experiment first.
4. Search AstrBot-native precedent before inventing a plugin-side mechanism; use adjacent mature projects only when the host lacks precedent.
5. For a bug, record symptom -> failing layer -> preconditions -> what it proves -> what it does not prove -> whether it generalizes.
6. Construct at least one legitimate counterexample path and one non-regression path before broadening a rule.
7. Run the narrowest relevant test first, then the owning integration suite, then real E2E only when the evidence level and regression impact require it.
8. Record newly discovered objective conditions when they materially change strategy.
9. Continue routine observe -> attribute -> minimally modify -> re-test -> record loops without repeated confirmation.

## Stop conditions

Stop and request a design decision only when a change would deliberately transfer ownership between AstrBot, this plugin, the user, QQ/NapCat, and the upstream provider/model, or when two legitimate strategies have materially different product semantics. Routine implementation, testing, documentation synchronization, harness correction, regression fixes, and release preparation should continue automatically.
