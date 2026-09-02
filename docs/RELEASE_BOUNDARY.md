# Release and Repository Boundary

Lifecycle role: current WARM boundary. Current version/candidate state lives only in `docs/PROJECT_STATE.json`.

## One durable product source

The GitHub default branch `main` is the only durable installation, version and publication source. Its repository root must itself be a complete AstrBot plugin.

There is no supported secondary runtime/generated/rollback/version publication branch. A temporary PR branch exists only for review and validation; it is never an install URL or marketplace authority. After release, stale non-main refs must be deleted when possible or force-collapsed to the exact released `main` commit so they cannot contain an alternate plugin tree/version.

## Runtime dependency boundary

Production Python is rooted at `main.py` / `__init__.py` and may depend only on runtime modules/assets in the repository root, `adapters/`, `capabilities/`, `compatibility/`, and `metadata/`.

Tests and current documentation may coexist in the repository, but production code must not import them. Historical experiments do not need a second branch or current-tree state archive; Git history preserves them.

## Public-information boundary

Never track:

- API keys, tokens, passwords, private keys, credential-bearing URLs;
- private AstrBot config, account/chat state or identifiable logs;
- private screenshots/media;
- `.env`, caches, bytecode, build output, dependencies or generated release archives.

Large runtime evidence belongs in short-lived CI artifacts rather than the plugin tree.

## Identity and rollback

`metadata.yaml` on `main` is the installation identity and uses a strictly increasing three-part version. Its `repo` is always the repository root.

A bad exposed version is never repaired by making an older/broken tree “latest” or rewriting the same version. Restore known-good behavior in a **higher** version and pass the current real-browser/lifecycle gates before publication.

A Git tag/Release is only a traceable snapshot and cannot override a different `metadata.yaml` on `main`.

## Observable release gate

For a model-card release, the blocking product proof is user-visible state in a real running AstrBot Dashboard: owned Ark + Agent Plan cards show exactly one native Video checkbox, visible click checks it, save/reopen/restart retain it, advanced request rows including `custom_extra_body` remain usable, foreign cards remain clean, and uninstall removes plugin UI.

See `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` and `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`.
