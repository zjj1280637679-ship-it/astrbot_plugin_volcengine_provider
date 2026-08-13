## Change identity

- Track: <!-- stable regression | experiment | release candidate | documentation only -->
- Object changed: <!-- runtime | Dashboard | packaging | evidence | documentation -->
- Stable release changed: <!-- no | yes, version -->
- `PROJECT_STATE.verdict.active_release_candidate`: <!-- null | exact candidate object -->

## Expected transition

<!-- Write the complete before -> action -> after path. Do not describe only the first visible step. -->

## Evidence by object

| Object / layer | Required result | Receipt | Status |
|---|---|---|---|
| | | | UNMEASURED |

Allowed status: `PASS`, `FAIL`, `UNMEASURED`. Do not replace this table with one aggregate success claim.

## Non-regression

- [ ] Foreign provider behavior is unchanged, or the intentional change is stated.
- [ ] The generated runtime allow-list is unchanged, or the runtime consumer is stated.
- [ ] Stable workflow identities were not repurposed for an experiment.
- [ ] Failed or stopped experiments are `releaseable: false` and archived.

## Release decision

- [ ] This change is **not** being presented as a release candidate.
- [ ] Or every blocking condition passed and `PROJECT_STATE` explicitly names the candidate.
