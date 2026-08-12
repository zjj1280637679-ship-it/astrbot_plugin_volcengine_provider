# ADR-0005: One HOT state authority with warm/cold demotion

Status: **Accepted**

## Context

The project intentionally keeps rich historical evidence, release notes, ADRs, strategy graphs, test history, and machine-readable state. That memory is useful, but several documents had begun to carry independent present-tense statements about the current release, current strategy, and active validation frontier.

During 0.1.19 development, `PROJECT_STATE.json`, `DECISION_INDEX.json`, `AI_ONBOARDING.md`, and `DESIGN_DECISIONS.md` still described parts of the completed 0.1.18 Source-UI frontier as current. The facts were not necessarily false; their **lifecycle role was stale**. This can pull future humans/agents back toward an old goal even when the implementation target has changed.

## Decision

1. `docs/PROJECT_STATE.json` is the single **HOT/current state authority**.
2. Other documents are WARM/COLD explanation or history and must reference HOT state instead of copying the current goal/frontier.
3. Completed release frontiers are demoted to `docs/archive/` summaries or existing historical ledgers.
4. Rejected/superseded strategies are retained with status and reconsideration/invalidator conditions rather than deleted.
5. A lightweight CI guard checks that the candidate version and active frontier in `PROJECT_STATE` match `metadata.yaml`, and that `DECISION_INDEX` remains navigation rather than a second active-state store.

## Consequences

Positive:

- version changes have one state file to update;
- old requirements remain searchable without remaining action-driving;
- invalidators/reconsideration conditions preserve useful history;
- future agents can distinguish current goal from still-valid stable constraints;
- stale duplicated `active_evidence` sections become structurally detectable.

Costs:

- release/version bumps must update `PROJECT_STATE` in the same change;
- warm documents should avoid present-tense release snapshots and link to HOT state instead;
- some old strategy files need explicit lifecycle metadata.

## Scope correction discovered with 0.1.19

ADR-0003 remains valid for the **shared top capability/modalities extension problem** that caused the video checkbox to appear everywhere or nowhere. It must not be overgeneralized into “no provider-specific model-card body fields are possible.”

0.1.19 demonstrated that ordinary saved-model edit-body rows can be safely projected onto owned model-card copies because AstrBotConfig renders keys actually present on that model object. That narrower mechanism does not reopen the rejected top capability-row strategy.

## Invalidators / reconsideration

Reconsider this ADR only if the project gains a generated single-source documentation system that makes multiple current-state views mechanically derived from one source, or if AstrBot/runtime begins consuming project documentation as an explicit supported control plane (which would itself require a new ownership decision).
