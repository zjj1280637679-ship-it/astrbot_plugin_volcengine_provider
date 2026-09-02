# Knowledge Lifecycle

## One current-state authority

`docs/PROJECT_STATE.json` is the only HOT/current release-state authority. Other documentation may define durable constraints, but it must not maintain an independent current version, release candidate, blocker list or active frontier.

## Current-tree policy

The working tree should be easy for a new maintainer or AI to read without reconstructing a state machine from years of superseded prose.

Use three classes:

- **HOT** — current release identity, goal and blocking acceptance; only `PROJECT_STATE`.
- **WARM** — durable constraints that still apply, such as `AGENTS.md`, the current release spec and the current model-card contract.
- **HISTORY** — superseded/rejected/invalidated release details; preserved in Git history and concise CHANGELOG lessons, not as competing present-tense project state.

There is no current-tree `docs/archive/` state layer. A failed candidate does not need a second file tree to remain remembered; Git already preserves the exact failed commit.

## Promotion and demotion

1. Start a candidate by updating `PROJECT_STATE` to `validating / releaseable:false`.
2. Keep the candidate non-releaseable while any blocking observable gate is red or unmeasured.
3. If the strategy changes, update the current WARM contract/decision in place and let Git preserve the previous text.
4. If the candidate fails permanently, close/abandon it; do not publish it and do not create an alternate durable branch or archive snapshot.
5. If every blocking gate passes on the exact candidate SHA, mark that SHA `ready / releaseable:true` and rerun required checks.
6. After merge, project `PROJECT_STATE` to stable on `main` and collapse/delete stale non-main refs.

## Conflict rule

If an older document contradicts `PROJECT_STATE`, `AGENTS.md`, `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` or `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`, the older statement is stale and must not drive implementation. Update or remove it in the same change when practical.

## Evidence identity

Evidence only proves the layer it observed:

- compile/import: structural loadability;
- unit/contract: deterministic code invariants;
- real Dashboard: visible UI/interaction;
- process restart: persistence/lifecycle;
- raw provider API: downstream protocol edge;
- QQ/NapCat/AstrBot run: complete product path;
- marketplace listing: external indexing only.

A green lower layer never upgrades a red or unmeasured higher-layer product requirement.

## Historical helper filenames

Versioned test helper filenames may remain when they are reused internally and still encode valid regressions. They are implementation history, not release authority. Active CI must enter through version-neutral current contract entrypoints named by `PROJECT_STATE`.
