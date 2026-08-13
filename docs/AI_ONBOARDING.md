# AI Onboarding

Lifecycle role: **WARM entry point**. This document explains stable project structure and working method. It is **not** the current release/goal authority.

**Read the `verdict` object in `docs/PROJECT_STATE.json` first.** It tells you separately which release is stable, whether a release candidate exists, which external states remain unmeasured, and which experiments are stopped. Read `docs/KNOWLEDGE_LIFECYCLE.md` before treating older present-tense text as action-driving.

## Purpose

This document lets an AI or new maintainer reconstruct the project quickly without treating historical conversation context, test output, screenshots, one successful interaction, or a completed release goal as hidden authority.

## Project map

| Area | Purpose | Start here |
|---|---|---|
| HOT current state | Current version, goal, strategy, blockers/frontier | `docs/PROJECT_STATE.json` |
| Knowledge lifecycle | HOT/WARM/COLD, superseded/rejected/invalidated handling | `docs/KNOWLEDGE_LIFECYCLE.md` |
| AI modification rules | Ownership and safe-edit boundaries | `docs/AI_RULES.md` |
| Knowledge boundary | Interaction vs evidence vs judgment | `docs/KNOWLEDGE_BOUNDARY.md` |
| Engineering method | Epistemic pipeline, interface-existence rule, bounded iteration | `docs/ENGINEERING_METHODOLOGY.md` |
| Evidence semantics | What each kind of result can and cannot prove | `docs/EVIDENCE_LEVELS.md` |
| Test ownership | Which layer each test may judge | `docs/TEST_BOUNDARIES.md` |
| Historical validation | Important successful paths and what they proved | `docs/TEST_HISTORY.md` |
| Regression impact | When historical evidence becomes stale and must be rerun | `docs/REGRESSION_SCOPE.md` |
| Stable design decisions | Objective conditions, constraints, rejected strategies | `docs/DESIGN_DECISIONS.md`, `docs/ADR/` |
| Decision navigation | WARM index only; never current-state authority | `docs/DECISION_INDEX.json` |
| Cold state | Completed/superseded release-state summaries | `docs/archive/` |
| Stopped 0.1.20 Video-checkbox experiment | Partial passes, blocking failure, stop condition | `docs/archive/EXPERIMENT-0.1.20-source-scoped-video.md` |
| Provider runtime | AstrBot provider integration and Ark/Agent Plan calls | `providers.py`, `main.py` |
| Media adapters | Last-mile audio/video payload construction | `adapters/audio.py`, `adapters/video.py` |
| Input failure provenance | Distinguish local transport failure from upstream/model response | `adapters/errors.py` |
| Dynamic model feedback | Translate current Ark `/models` response for the current Source response only | `metadata/ark.py`, `capabilities/source_hints.py` |
| Agent Plan model listing | Agent Plan model-name discovery without model-ID capability priors | `metadata/agent_plan.py` |
| Model-card request config | Volcengine-owned per-model request fields and migration | `capabilities/model_fields.py`, `capabilities/model_fields_bridge.py`, `capabilities/model_scope.py` |
| 0.1.18 Source UI bridge | Owned-Source video presentation and Source-save translation | `registry.py` |
| Machine semantics | Stable meanings for capability/feedback/config fields | `capabilities/SEMANTICS.json` |
| Persistent regressions | Current contract tests | `tests/test_*` |
| Product-path evidence | Host integration, UI evidence, real API attribution | `docs/E2E_MATRIX.md` |
| Historical model/video research | Preserved observations and decisions; no active workflow authority | `evidence/`, `governance/`, `strategy/` |

## Stable objective conditions

These conditions survive individual release goals unless a later ADR explicitly invalidates them:

- Volcengine Ark can expose first-party Doubao/Seed models and third-party/open models through the same provider platform.
- Model/platform behavior can change over time; model-ID capability inference is not permanent truth.
- AstrBot owns provider lifecycle, routing/fallback/retry, provider-source/model-card management, metadata display, and shared Dashboard rendering.
- Capability icons/metadata are incomplete feedback surfaces, not a complete model-capability truth table.
- A model may support a modality while the complete QQ/NapCat/AstrBot/provider transport path is broken; a raw synthetic fixture is not equivalent to the product path.
- The shared **top capability/modalities** surface is not a safe provider-specific extension boundary for the fifth Volcengine video capability control. The stable 0.1.18/0.1.19 Source UI remains the released solution for that specific problem.
- The stopped 0.1.20 private-dialog-clone experiment made `Video` visible only on owned create dialogs, but the saved owned cards lost the matching video mode row after reopen. Do not cite its create-dialog pass as a complete feature or resume it without satisfying its archived reconsideration condition.
- This does **not** imply that ordinary saved-model edit-body rows are impossible. 0.1.19 uses a narrower owned-model projection path for ordinary horizontal request settings; see ADR-0005 and `PROJECT_STATE`.
- Historical QQ-oriented media validation is retained and re-run by dependency impact, not by release number alone.

## The five questions to answer before editing

1. **Objective condition:** What has actually been observed rather than assumed?
2. **Expected outcome:** What user-visible or protocol-visible behavior is required by the HOT goal?
3. **Current owner:** Which layer owns that behavior: QQ/NapCat, AstrBot, this adapter, the user, or upstream?
4. **Counterexample:** What legitimate path would break if this rule generalized too far?
5. **Regression edge:** Which historical evidence becomes stale if this dependency changes?

Then classify the strongest evidence using `docs/EVIDENCE_LEVELS.md` and verify that the proposed action is still HOT rather than historical/superseded.

## Stable strategy constraints

These are not a replacement for the current strategy in `PROJECT_STATE`; they constrain future strategies:

- Keep runtime/request transport configuration distinct from AstrBot `modalities` capability truth.
- Keep Volcengine-specific fields isolated from foreign providers.
- Keep ordinary Ark `/models` feedback transient, Source-scoped, single-use, and async-context isolated.
- Preserve explicit `false`, empty lists, integer `0`, and unknown future modality tokens when upstream explicitly provides them.
- Preserve migration intent without promoting wrong-Source/foreign debris into authority.
- Keep routing/fallback/retry ownership in AstrBot unless a new explicit architecture decision transfers ownership.
- Attribute failures by layer before changing production code.
- Use `TEST_HISTORY` + `REGRESSION_SCOPE` before deciding whether expensive QQ-equivalent media validation is required.
- Never broaden production media code merely to make a non-equivalent raw fixture pass.

## Safe AI workflow

1. Read `PROJECT_STATE.verdict` first, then this project map. Load only the relevant lifecycle/rule/ADR/test documents for the affected object.
2. Inspect the current branch and changed-file impact before proposing abstractions.
3. For every arrow in a proposed flow, identify the concrete host/plugin/upstream interface that carries it. If unknown, run a minimal existence experiment first.
4. Search AstrBot-native precedent before inventing a plugin-side mechanism.
5. For a bug, record symptom -> failing layer -> preconditions -> what it proves -> what it does not prove -> whether it generalizes.
6. Construct at least one legitimate counterexample and one non-regression path before broadening a rule.
7. Run the narrowest relevant test first, then the owning integration suite, then real E2E only when the evidence level/regression impact requires it.
8. When a new discovery materially changes the current strategy, update `PROJECT_STATE` once; add an ADR only if the rule should survive the current release.
9. When a goal completes or is replaced, demote it to history/cold storage instead of leaving a second present-tense frontier.
10. Continue routine observe -> attribute -> minimally modify -> re-test -> record loops without repeated confirmation.

## Stop conditions

Stop and request a design decision only when a change would deliberately transfer ownership between AstrBot, this plugin, the user, QQ/NapCat, and the upstream provider/model, or when two legitimate strategies have materially different product semantics. Routine implementation, testing, documentation synchronization, harness correction, regression fixes, lifecycle demotion, and release preparation should continue automatically.
