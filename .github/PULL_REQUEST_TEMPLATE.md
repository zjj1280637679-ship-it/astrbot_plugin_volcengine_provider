## Change identity

- Track: <!-- stable regression | release candidate | experiment | documentation only -->
- Object changed: <!-- runtime | Dashboard | release topology | evidence | documentation -->
- Stable release changed: <!-- no | yes, version -->
- `PROJECT_STATE.verdict.active_release_candidate`: <!-- null | exact candidate object -->

## Expected transition

<!-- Write the complete before -> action -> after path. -->

## Evidence by object

| Object / layer | Required result | Receipt | Status |
|---|---|---|---|
| | | | UNMEASURED |

Allowed status: `PASS`, `FAIL`, `UNMEASURED`. Do not replace layer-specific evidence with one aggregate success claim.

## Non-regression

- [ ] `main` remains the only durable installation/version/publication truth.
- [ ] Foreign Provider cards remain free of plugin-only UI/config fields.
- [ ] If model-card UI changed, the real Dashboard contract covers visible Video click/check/save/reopen and request-field visibility/persistence.
- [ ] If lifecycle/release topology changed, real restart/update/uninstall acceptance is included.
- [ ] No obsolete runtime/generated/rollback publication branch or current-tree failed-state archive was introduced.

## Release decision

- [ ] This change is not a release candidate.
- [ ] Or `PROJECT_STATE` names a validating candidate with `releaseable: false` and every blocker remains explicit.
- [ ] Or every blocking observable condition passed on the exact SHA and `PROJECT_STATE` names a ready releaseable candidate.
