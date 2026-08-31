# Knowledge Lifecycle / 知识生命周期

## Purpose

This repository preserves a large amount of useful history. The risk is not lack of documentation; it is **historical state continuing to look current after the project goal moves**.

This document defines one lifecycle so requirements, goals, evidence, and strategies can age without accumulating into a second hidden control plane.

## Single hot-state authority

`docs/PROJECT_STATE.json` is the **only HOT authority for current development state**.

Its `verdict` keeps stable release, active release candidate, external observation, and experiment as separate identities. A pass or failure attached to one identity must never be promoted to another identity.

It owns only information that can legitimately answer questions such as:

- What version/branch is being developed now?
- What is the current user goal?
- Which constraints are frozen for this iteration?
- What strategy is active now?
- What validation frontier is still open?
- Which recent red/green signals are known harness failures rather than product verdicts?

Other documents may explain stable rules or history, but they must not maintain an independent copy of the current goal/frontier.

## Lifecycle classes

### HOT — current and action-driving

Examples:

- current release candidate;
- current goal and non-goals;
- current implementation strategy;
- current validation frontier;
- unresolved blocker or known false-failure affecting the next action.

Rules:

1. HOT state lives in `docs/PROJECT_STATE.json`.
2. A version/goal change must update HOT state in the same PR.
3. HOT statements elsewhere should be references to `PROJECT_STATE`, not duplicated narratives.

### WARM — valid constraints or reusable evidence

Examples:

- ADRs whose ownership boundaries still apply;
- `DESIGN_DECISIONS.md` stable constraints;
- `REGRESSION_SCOPE.md` impact rules;
- evidence whose premises have not been invalidated;
- current strategy metadata for a separate subsystem that is not the active release goal.

WARM material may constrain a new solution, but it does not become the current goal merely because it is still valid.

### COLD — historical, superseded, rejected, or invalidated

Examples:

- completed release frontiers;
- old `PROJECT_STATE` snapshots;
- superseded strategy versions;
- rejected approaches;
- obsolete requirements;
- evidence whose invalidator fired.

COLD material is retained to prevent amnesia and repeated mistakes. It may be reconsidered only when its explicit `reconsider_if` / invalidator conditions make it relevant again.

## Required lifecycle vocabulary

For machine-readable objects, prefer these states:

- `active`
- `candidate`
- `warm`
- `historical`
- `superseded`
- `rejected`
- `invalidated`
- `stopped_after_failure_limit`

When useful, record:

```json
{
  "status": "superseded",
  "scope": "what this statement actually governed",
  "introduced_in": "0.1.18",
  "superseded_in": "0.1.19",
  "superseded_by": "new object/path/id",
  "invalidators": [],
  "reconsider_if": [],
  "last_verified": "2026-08-12"
}
```

## Four drift classes to detect explicitly

### Obsolete requirement / 过期需求

A requirement is cold when it is completed, replaced, or its enabling condition disappears. It must not continue to drive implementation just because an old design document uses present tense.

### Invalidated premise / 失效条件

Evidence and decisions should retain their invalidators. When an invalidator fires, the old object becomes a baseline to re-check, not current authority.

### Drifted goal / 漂移目标

A goal that was correct for an earlier release becomes cold when the active release goal changes. Completed external-observation frontiers must not occupy the active frontier of a new implementation release.

### Rejected or false strategy / 假策略

Rejected strategies stay recorded with the counterexample/reason that killed them. They are not silently deleted, but they are also not eligible for implementation unless a stated `reconsider_if` condition fires.

### Half-closed experiment / 半闭环实验

An experiment is not a release candidate merely because some layers passed. If a blocking transition remains open, record the passed and failed objects separately, set `releaseable: false`, and move the experiment to `docs/archive/` when its stop condition fires. A later green job in an unrelated layer does not reopen it.

## Document roles

- `docs/PROJECT_STATE.json` — **HOT** current state only.
- `AGENTS.md`, `docs/AI_ONBOARDING.md` — WARM entry points; point to HOT state instead of duplicating it.
- `docs/DESIGN_DECISIONS.md`, `docs/ADR/**` — WARM stable decisions and rejected-strategy memory.
- `docs/TEST_HISTORY.md`, `CHANGELOG.md` — COLD/WARM historical evidence depending on invalidators; never current-goal authority.
- `docs/REGRESSION_SCOPE.md` — WARM rules for deciding when old evidence becomes stale.
- `docs/DECISION_INDEX.json` — WARM navigation only; it must not contain a second `active_evidence`/release frontier.
- `docs/archive/**` — explicitly COLD snapshots/summaries.
- `strategy/*vN*` — each version should say whether it is active/warm or superseded.

## Promotion / demotion rules

1. New release goal -> update `PROJECT_STATE` first.
2. Previous HOT release/frontier -> demote to `docs/archive/` summary or an existing historical ledger.
3. New decision -> add stable rule to ADR/design docs only if it should survive the current release.
4. New evidence -> record domain + premises + invalidators; do not promote it to HOT unless it changes the next action.
5. Superseded strategy -> mark `superseded_by`; do not leave two versions looking equally current.
6. Rejected strategy -> preserve reason/counterexample; do not erase it.
7. Experimental workflow -> use a new `EXPERIMENT` workflow identity; never rewrite a stable workflow and inherit its historical name.

## CI guard

`tools/release/check_main_install_source.py` is the active release drift guard.
It checks that `metadata.yaml`, README, CHANGELOG, and the candidate/stable state
in `docs/PROJECT_STATE.json` identify the same version. It also verifies that
the default `main` root contains the complete runtime closure and configuration
schema expected by the documented feature set.

The guard intentionally leaves historical release references untouched. It
rejects only current-authority or installation-source drift; old evidence may
retain the version and branch identity under which it was observed.
