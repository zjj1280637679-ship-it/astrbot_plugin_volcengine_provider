# AI Onboarding

Role: **current navigation only**. This file never defines the active release state by itself.

## Read order

1. `docs/PROJECT_STATE.json` — the only HOT/current release authority.
2. `AGENTS.md` — non-negotiable branch, ownership and real-UI acceptance rules.
3. `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md` — exact owned model-card Video/request-field product contract.
4. `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` — release and publication policy.
5. Only then inspect the production module or regression relevant to the change.

Do not reconstruct current intent from old version numbers, branch names, old workflow names, historical test helper names or Git history. Git history is audit material, not a second control plane.

## Current project map

| Object | Current owner |
| --- | --- |
| Stable/candidate identity and blocking gates | `docs/PROJECT_STATE.json` |
| Single publication truth | `main` |
| Provider registration/lifecycle | `main.py`, `registry.py`, AstrBot host |
| Ark / Agent Plan protocol | `providers.py`, `metadata/` |
| Audio/video/image last mile | `adapters/` |
| Owned model-card request fields | `capabilities/model_fields.py`, `capabilities/model_fields_bridge.py` |
| Owned model-card UI adaptation | `capabilities/dashboard_asset_bridge.py`, `capabilities/dashboard_runtime_bridge.py` |
| Concrete Source/card ownership | `capabilities/model_scope.py` |
| Current real browser gate | `tests/e2e/provider_card_matrix/current_release_ui_contract.py` |
| Current restart/update/uninstall gate | `tests/e2e/provider_card_matrix/current_lifecycle_contract.py` |

## The core object distinction

A Provider Source is not a concrete model card.

The current Video feature belongs to one concrete owned model card's native AstrBot `modalities` checklist. It must not be replaced by a Source-level master switch, Source selector, hidden boolean, model metadata icon or process-global shared-schema Video option.

The same concrete owned card must preserve AstrBot's `custom_extra_body` and expose the plugin's typed request rows. Those rows are product UI, not optional debugging metadata.

## Release evidence hierarchy

For a UI/release change:

- compile/import/no-conflict evidence is necessary but weak;
- deterministic unit/contract tests are necessary but still insufficient;
- the blocking product evidence is a real built AstrBot Dashboard driven through visible controls;
- saved state must survive reopen and real AstrBot restart;
- unload must remove public UI residue.

Do not promote a release because a lower evidence layer is green while the visible model-card contract is red or unmeasured.

## Stable ownership boundaries

- AstrBot owns provider lifecycle, routing, retry and fallback.
- The plugin owns Volcengine-specific protocol/media translation and its own per-card request-field projection.
- Provider identity is not permanent model-capability truth.
- Missing upstream feedback is not `false`.
- A local transport failure is not proof that a model lacks a modality.
- Foreign Provider cards must remain free of plugin UI/config fields.
- Runtime secrets, chat/account state and generated local artifacts never belong in Git.

## Working rule

When you discover a conflict between an old document and `PROJECT_STATE` + `AGENTS` + the current model-card contract, the old document is stale. Update or remove it in the same change; do not preserve contradictory present-tense guidance in a new archive folder.
