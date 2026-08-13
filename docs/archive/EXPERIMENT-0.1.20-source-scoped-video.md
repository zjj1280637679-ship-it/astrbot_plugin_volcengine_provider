# Archived experiment: 0.1.20 source-scoped Video checkbox

> **Status: stopped, not merged, not released, and not a release candidate.**
>
> Stable user release: **0.1.19** from the `runtime` branch.

## Question tested

Could the plugin add `video` to the existing model-card `modalities` checklist for Volcengine Ark and Agent Plan only, while leaving foreign provider cards unchanged?

## Object boundaries

| Object | Result | What it proves |
|---|---|---|
| Minimal runtime package | PASS | The experimental package was structurally valid. |
| AstrBot 4.26.1 / 4.27.2 loading | PASS | The plugin could register and load on those hosts. |
| Ark / Agent Plan create dialog | PARTIAL PASS | `Video` appeared and could be selected during creation. |
| Foreign OpenAI create dialog | PASS | `Video` did not leak into that foreign card. |
| Saved Ark / Agent Plan edit dialog | FAIL | After save and reopen, `_volcengine_video_input_mode_ui` was missing. |
| Release / marketplace | NOT ATTEMPTED | No experiment artifact was merged or published. |

These receipts are intentionally not collapsed into one `success` Boolean. The experiment reached presentation isolation but did not close the create -> save -> reopen lifecycle.

## Attempts and stop line

The real Dashboard evidence job failed three consecutive implementation attempts:

1. `31718426558`
2. `31719239572`
3. `31719539311`

The final run showed:

- Ark and Agent Plan: `Video` present in the create checklist;
- OpenAI: no `Video` option;
- Ark and Agent Plan: saved model reopened without `_volcengine_video_input_mode_ui`;
- page errors: none.

The agreed three-failure stop line therefore fired. PR #10 was renamed `[ARCHIVED EXPERIMENT]` and closed. Its branch and CI logs remain available as evidence, but they are not action-driving.

## Why the repository became misleading

Three independent identities were accidentally coupled:

1. the stable `0.1.19` release;
2. the experimental `0.1.20` branch;
3. the stable workflow file and its GitHub display identity.

The experiment changed the contents of the stable 0.1.19 workflow instead of creating a separately named experimental workflow. GitHub therefore displayed failed 0.1.20 evidence under the historical 0.1.19 workflow name. At the same time, the experimental branch called itself a `release_candidate` before its blocking save/reopen contract passed.

## Reconsider only if

A future design may revisit this idea only when it first supplies a bounded test for all three transitions:

```text
owned Source selected
        -> private create-dialog schema contains video
        -> saved canonical value is retained
        -> reopened edit dialog contains the owned video row
```

It must use a separately named experimental workflow and must not modify the stable 0.1.19 verdict while still experimental.
