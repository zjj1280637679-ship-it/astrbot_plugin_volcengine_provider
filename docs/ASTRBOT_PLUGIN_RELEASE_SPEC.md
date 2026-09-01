# AstrBot Plugin Release Specification

Status: current project release policy for `astrbot_plugin_volcengine_provider`.

## 1. One installation source

The repository default branch, `main`, is the only active installation and
version authority. Its root must always contain a complete AstrBot plugin:

```text
metadata.yaml
main.py
__init__.py
_conf_schema.json
providers.py
registry.py
adapters/**
capabilities/**
compatibility/**
metadata/**
logo.png
README.md
CHANGELOG.md
LICENSE
```

The historical `runtime` branch is recovery evidence only. It must not receive
new versions, appear in `metadata.repo`, or become a second marketplace source.
Temporary review branches are allowed, but every published byte is merged into
`main`.

This follows AstrBot's current plugin publishing model: the official Collection
validator clones the repository default branch and loads the plugin from its
root. The canonical repository URL is:

`https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider`

## 2. Version and identity

- `metadata.yaml` is the version source for an installable checkout.
- Versions use unsigned SemVer, for example `0.1.34`; Git tags may add `v`.
- Any changed runtime behavior or installation payload requires a strictly
  newer version. Never rewrite an already exposed version in place.
- `name` and `author` form the marketplace identity and must remain stable.
- `repo` must be the HTTPS repository root, never a branch, subdirectory,
  Issue, PR, or Release page.
- `astrbot_version` uses PEP 440. The declared floor is `>=4.26.1`; tested host
  versions are evidence, not a reason to add an unapproved future-version load
  gate.
- `README.md`, `CHANGELOG.md`, and `docs/PROJECT_STATE.json` must agree with
  the metadata version and its candidate/stable lifecycle state.

## 3. Public repository boundary

AstrBot may download the default-branch archive, so every tracked file is
public distribution material even when Python never imports it. The repository
must not contain credentials, private configuration, private or identifiable
account state, chat data, local captures, cache files, build output, or
development secrets. De-identified historical measurements that were already
intentionally published may remain as audit evidence, but must not contain
secret values, personal identifiers, or credential-bearing URLs.

Tests, CI, ADRs, and evidence may coexist with runtime code. Production modules
must not import or depend on them. Required runtime modules must never live only
in another branch or an untracked local directory.

The source ZIP must stay below AstrBot's 16 MB publication limit. Large test
media and generated artifacts remain outside the tracked installation source.

## 4. Release gates

Every candidate must pass both static and running checks:

1. `tools/release/check_main_install_source.py` verifies metadata, root runtime
   closure, configuration schema, version ledgers, logo shape, Python syntax,
   tracked-path hygiene, high-confidence secret patterns, and the size budget.
2. All deterministic top-level regression scripts run in the Launcher-managed
   AstrBot environment.
3. The model-card Video and lifecycle contracts run against AstrBot 4.27.3 and
   4.27.4. Owned Ark and Agent Plan cards must each expose exactly one Video
   option; foreign cards must remain clean; save/reopen and unload must work.
4. A real restarted Launcher instance must serve the repaired Dashboard bundle.
   Reading source or passing a mocked test is not a substitute for that visual
   and persistence evidence.
5. The candidate diff and tracked history are scanned for credentials and
   unexpected large files. Real Ark/DeepSeek paid workflows are not dispatched
   unless a change affects those protocol edges and the maintainer authorizes
   the external call.

## 5. Publication flow

1. Start from the current remote `main`; never force-push over unseen work.
2. Prepare one review branch, bump the patch version, update the release ledger,
   mark it as `validating` / `releaseable: false`, and complete the local gates
   that do not depend on the PR or authenticated restarted Dashboard.
3. Push with an explicit refspec, open a PR to `main`, and wait for every
   expected non-paid check to finish successfully.
4. Complete the authenticated restarted-Launcher UI check and final code/release
   review. Every blocking acceptance condition must now have an observed pass.
5. Convert the exact PR head into the final stable merge tree: set
   `stable_release` to the new version, clear `active_release_candidate`, project
   the stable state into README, run `check_main_install_source.py
   --require-releaseable`, push that state-only commit, and wait for the expected
   checks again on that exact SHA. This projection is merge-ready, not a claim
   that the commit is already present on public `main`.
6. Merge the exact reviewed stable-projection commit. Do not update `runtime`;
   verify that remote `main` contains the reviewed tree.
7. Optionally tag the merged commit as `v<version>` and create a GitHub Release
   for traceability. The tag does not replace `metadata.yaml` or update the
   AstrBot market by itself.
8. For marketplace publication, submit the root repository through AstrBot
   Cloud's plugin publishing page. After approval/indexing, confirm the public
   marketplace record and perform a clean install/update from the repository.

If a public release is bad, publish a reviewed higher patch version containing
the correction or revert. Do not reset public history or reuse the old version.

## 6. Evidence boundaries

A green GitHub Release proves only that GitHub accepted a tag/release. A green
load test proves only loading. Neither proves marketplace refresh, model-card
persistence, a real Ark response, or a QQ/NapCat end-to-end path. Record each
receipt at the layer it actually observed in `docs/TEST_HISTORY.md` and keep
unmeasured cells explicit.
