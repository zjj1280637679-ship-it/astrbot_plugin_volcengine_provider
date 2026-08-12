# Release Boundary

## Core rule

The development repository and the user distribution package are different products with different audiences and constraints.

- `main` is a **development state**: it may contain tests, CI, evidence, AI onboarding, ADRs, experiments, benchmark material, and other information useful to maintainers.
- `runtime` is a **distribution state**: it contains only the minimum runtime closure required for AstrBot to install and execute the plugin, plus legally/operationally required user-facing assets.

Development explainability must not be implemented by shipping the development knowledge base to users.

## Observed failure pattern

A previous store package was built from the repository archive directly. Development files such as `.github/workflows/**` entered the user package. On Windows, extraction failed partway through on long workflow paths, leaving a partial plugin directory; the next install then reported a directory/file-name conflict.

The same pattern also creates an information-boundary failure even when extraction succeeds: CI logic, internal test assets, evidence, experiments, and future confidential development material can be exposed to non-developers for no runtime benefit.

## Required topology

```text
Development repository (main)
  ├─ runtime source code
  ├─ tests / CI / benchmarks
  ├─ docs / ADR / AI hooks / evidence
  └─ private-or-development-only assets (never intentionally committed if secret)
              |
              | explicit allow-list build
              v
Runtime package / runtime branch
  ├─ metadata.yaml
  ├─ plugin Python runtime
  ├─ required logo/resource files
  └─ LICENSE
```

The release process is **allow-list based**, not deny-list based. A new development file is excluded by default until its runtime necessity is demonstrated.

## Runtime allow-list for this plugin

Root files:

- `metadata.yaml`
- `__init__.py`
- `main.py`
- `providers.py`
- `registry.py`
- `logo.png`
- `LICENSE`

Runtime Python packages:

- `adapters/*.py`
- `capabilities/*.py`
- `compatibility/*.py`
- `metadata/*.py`

Files such as `capabilities/README.md` and `capabilities/SEMANTICS.json` are development/explanatory assets unless production code begins to load them explicitly.

## Never distribute by default

The runtime artifact must not contain:

- `.git/`, `.github/`, workflows, or repository administration files;
- `tests/`, benchmark code, probes, CI harnesses, or test fixtures;
- `docs/`, ADRs, AI onboarding/rules, project state, evidence, governance, or development strategy;
- experiment/model-card research material and non-runtime test media;
- caches, temporary output, logs, coverage files, editor state, or build intermediates;
- credentials, `.env` files, tokens, API keys, passwords, private account data, private conversations, or confidential test data.

## Validation before publication

A release is not complete until the **artifact itself** is checked.

1. Build from the explicit runtime allow-list.
2. Verify required AstrBot metadata and entry files exist.
3. Verify forbidden paths are absent.
4. Scan the artifact for high-confidence secret patterns.
5. Reject abnormal package-size growth.
6. Compile/load the artifact in the supported AstrBot compatibility matrix.
7. Validate the same repository branch/archive form the AstrBot updater will consume.
8. Only then advance the marketplace-visible version.

A successful development checkout or CI run is not evidence that a distribution artifact is safe or installable.

## Repository/source binding

AstrBot officially accepts GitHub repository URLs with `/tree/{branch}` for plugin-market `repo` values. This project therefore binds marketplace/runtime installation to the stable `runtime` branch while keeping `main` as the development branch.

The `runtime` branch is generated. It must not become the place where development decisions, tests, or documentation are authored.
