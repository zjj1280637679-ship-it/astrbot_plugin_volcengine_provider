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
| Model-card transport config | Per-card canonical video request switch, Source display preference, and migration | `capabilities/model_scope.py`, `capabilities/source_migration.py` |
| Dashboard bridge | Owned-Source video selector projection and Source-save translation | `registry.py` |
| Machine semantics | Stable meanings for capability/feedback/config fields | `capabilities/SEMANTICS.json` |
| Persistent regressions | Current contract tests | `tests/test_*` |
| Product-path evidence | Host integration, UI evidence, real API attribution | `docs/E2E_MATRIX.md` |

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
- The shared generic model-card renderer does not provide a reliable owned-Provider identity boundary for an extra Volcengine field: previous attempts could render the field for every provider or for none. The Provider Source form owns the real Source identity and is therefore the current configuration surface.
- AstrBot 4.26.1's schema service can expose live provider dictionaries. A retired 0.1.17 Dashboard projection key may therefore be real upgrade residue, but only the boolean key encoding the card's exact `provider_source_id` carries user intent; same-prefix wrong-Source and foreign fields are cleanup-only debris.
- Both plugin-owned Ark and Agent Plan providers currently register as AstrBot `chat_completion`; Agent Plan is not an `agent_runner` UI card.
- A model may support a modality while the complete QQ/NapCat/AstrBot/provider transport path is broken, and the inverse test mismatch is also possible: a synthetic raw fixture may fail while an unchanged QQ-oriented path remains valid under its original conditions.
- The real AstrBot v4.27.2 Dashboard has been built, started, logged into, and opened at the Provider page with this plugin loaded. That is UI/host evidence, not model-capability evidence.
- The new Source-page selector save semantics pass the real AstrBot 4.26.1 and 4.27.2 service matrix (L3). A dated 2026-08-12 AstrBot 4.27.2 Dashboard DOM run also passed L4: Ark/Plan each had one master and one conditional selector containing only their own 2/1 cards; close hid the selector, reopen preserved the choice with zero API requests; foreign had 0/0; all Ark/Plan/foreign generic model dialogs contained none of the canonical, retired temporary, or new temporary video fields; `pageErrors=[]`. This is presentation evidence, not model-capability or media-path evidence.
- Fine Playwright provider-card automation encoded unstable harness assumptions and was retired as a release gate; coarse reachability plus evidence collection remains useful.
- Historical QQ-oriented media validation is tracked explicitly and must be re-run based on dependency impact, not because every release must reproduce every old E2E.

## Current expected outcome

- The plugin exposes the protocol ceiling it can transport without converting transport support into permanent model capability claims.
- User/model-card configuration controls whether a transport path is attempted; it does not manufacture a model capability fact.
- Current upstream feedback may be displayed for the current response, but stale plugin feedback must not survive to defeat a newer response.
- Errors identify where a request failed without taking ownership of AstrBot's routing decision.
- Provider-specific configuration remains isolated from foreign providers.
- Upgrade migration preserves the strongest exact owned-card intent, removes temporary/wrong-layer debris, and leaves AstrBot `modalities` unchanged.
- A failed host Source upsert restores Source/model-card state and manager mirrors to their pre-call snapshot. Because AstrBot may have saved before a later Provider reload fails, the plugin uses host `save_config()` for a compensating persistent rollback and best-effort reloads the old Source's cards; secondary failures do not replace the original host error and are attached as notes.
- Raw upstream tests are used for downstream protocol attribution, while QQ compatibility is judged only by a QQ-equivalent media path.
- Historical successful paths remain evidence until an impact edge invalidates their conditions.

## Current strategy

- Keep the runtime video transport truth per model card and out of AstrBot `modalities`.
- Put the configuration surface on owned Provider Sources: persist `volcengine_video_controls_visible` only as a show/hide preference, project a temporary checkbox list from the current Source's model-card IDs, and translate/remove that selector at the Source save boundary.
- Closing the Source display switch must preserve every per-card selection and runtime value; foreign Sources and generic model cards must receive no visible Volcengine video field.
- Keep ordinary Ark `/models` feedback transient, Source-scoped, single-use, and async-context isolated.
- Preserve explicit `false`, empty lists, integer `0`, and future unknown modality tokens when explicitly present in current feedback.
- Preserve legacy user intent with ADR-0004's exact precedence: canonical > exact-Source boolean retired 0.1.17 UI key > older per-card > legacy Source boolean including `false` > `modalities: video`; then remove all temporary/wrong-layer fields without promoting wrong-Source or foreign state.
- Treat Source selector write-back as a snapshot plus compensating rollback around the host upsert: restore Source/cards and manager mirrors, use host `save_config()` to persist that restored snapshot when available, best-effort reload the old Source's card instances, and re-raise the original host error. Annotate persistence/reload compensation failures and do not claim unobserved state was restored.
- Treat contract/service tests as hard gates according to ownership.
- Treat Playwright as coarse reachability plus presentation evidence, not as an authority on fine UI layout.
- Prefer AstrBot-native precedent and minimal existence experiments before constructing new automation around an assumed interface.
- Use `TEST_HISTORY` + `REGRESSION_SCOPE` before deciding whether audio/video needs a full QQ-equivalent rerun.
- Never broaden media production code merely to make a non-equivalent raw fixture pass.

## Current release

`0.1.18` is released at the repository and runtime-distribution layers. PR #4 was squash-merged to `main` at `22444f47154f4f88ff3157d6e6ffcce9ad2689f0`; main gate run `31589741300` passed. Publisher run `31589815606` passed prepare, all four pre-promotion native-installer cells, promotion, and all four blocking post-promotion cells. The stable `runtime` commit is `4586aa2eb573eb97a72baaaa152c727e3b35530e`: its 21 blobs are byte-for-byte identical to the gate artifact and its metadata reports 0.1.18.

The Source-page video selector, exact 0.1.17 live-schema residue migration, wrong-layer cleanup, and failed-upsert rollback remain the behavioral scope of 0.1.18. Their recorded contract, AstrBot `4.26.1` / `4.27.2` service, real `4.27.2` Dashboard presentation, generated-package, and native-installer evidence must not be generalized into a model-capability or QQ-product-path claim.

The first publisher run's post-release candidate deletion exposed a cleanup-only execution-context bug after the validated runtime was already promoted. PR #5 fixed it at main commit `9feb0d5902f4bdc88ea69b08f6d3bee25fcf8f2e` and made remote-ref checks fail closed; main gate `31590820116` and no-op publisher `31590908018` passed, the unchanged runtime tree was not promoted again, and the residual candidate branch was removed. The only remaining release frontier is external observation: AstrBot Store refresh and a real Windows Store installation have not yet been observed.

Current ordinary Ark `/models`, text, and image raw-vs-plugin checks provide downstream L5 attribution evidence. Current Agent Plan checks with an ordinary-Ark credential fail in both raw and plugin paths with the same authentication/account boundary and therefore do not justify a production-code change. Audio/video product compatibility is not redefined by those raw probes; see `TEST_HISTORY` and `REGRESSION_SCOPE`.

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
