# Release and Repository Boundary

Lifecycle role: **WARM design boundary**. Current release/version state remains
in `docs/PROJECT_STATE.json`.

## Default branch is the product source

AstrBot's current publication and Collection validation path clones the GitHub
repository's default branch. Therefore `main` must be a complete installable
plugin at its root. The project does not generate or promote a second runtime
branch.

The old `runtime` branch is historical recovery evidence. Its contents may help
repair a proven regression, but it has no current installation, metadata, or
publication authority.

## Runtime dependency boundary

The installed Python closure is rooted at `main.py` and `__init__.py` and may
depend only on runtime modules and assets in the repository root, `adapters/`,
`capabilities/`, `compatibility/`, and `metadata/`.

Development material may coexist in the public repository:

- `.github/`, `tests/`, `docs/`, `evidence/`, `governance/`, `strategy/`, and
  `model_cards/` explain, verify, or record the product;
- production modules must not import those paths;
- removing development material must never be required to make the plugin load.

This distinction protects runtime independence without inventing a second tree.

## Public-information boundary

Every tracked file can enter a GitHub source archive. Never track:

- API keys, tokens, passwords, private keys, or credential-bearing URLs;
- local AstrBot configuration, private or identifiable account state,
  chat/conversation data, or logs;
- screenshots or media containing private information;
- `.env`, cache directories, bytecode, build output, downloaded dependencies,
  or temporary release archives.

The repository archive must remain under AstrBot's 16 MB limit. Large evidence
belongs in short-lived CI artifacts or an explicitly approved external store,
not in the plugin repository.

De-identified historical measurements already intentionally published may
remain as audit evidence only when they contain no secret values, personal
identifiers, or credential-bearing URLs. They are not runtime dependencies.

## Identity and rollback boundary

`metadata.yaml` at the `main` root is the installation identity. Its `repo`
points to the repository root and its version increases for every changed
public payload. A Git tag or Release is a snapshot, not a second authority.

Rollback is forward-moving: restore the last known-good behavior in a strictly
higher patch version. Never force-reset public `main`, reuse an exposed version,
or resume publication from the historical `runtime` branch.

The executable release procedure and gates are defined in
`docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md`.
