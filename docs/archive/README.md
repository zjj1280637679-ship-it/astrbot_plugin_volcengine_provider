# Cold Archive / 冷区

Files in this directory are intentionally **not current project authority**.

They preserve completed release frontiers, superseded state summaries, or other historical context that remains useful for regression and audit work.

Rules:

- Do not infer the current release goal or strategy from this directory.
- Use `docs/PROJECT_STATE.json` for HOT/current state.
- Historical evidence can still be valid within its recorded premises; use `docs/REGRESSION_SCOPE.md` to decide whether an invalidator requires revalidation.
- A cold item may return to active consideration only when an explicit invalidator/reconsideration condition fires.

## Retired executable probes

Completed one-off Seedance workflows were removed from `.github/workflows` on 2026-08-14 so they no longer appear as active project operations or risk accidental paid execution. Their conclusions remain in `evidence/`, their decisions remain in `governance/`, and their exact executable definitions remain recoverable from Git history. Historical executability is not current workflow authority.
