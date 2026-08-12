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

`metadata.yaml` is the release-version source for the active distribution
chain. The builder copies that value into the runtime manifest; candidate and
installed-package validators compare their own `metadata.yaml` with that exact
manifest. Active release workflows must not duplicate the current plugin
version as a numeric literal. Release versions use three unsigned numeric
parts. If the generated runtime tree differs from the current `runtime` tree,
its version must be strictly newer; identical trees remain a no-op.

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

A release is not complete until the **artifact itself** and the exact user-facing
source have been checked.

1. Run the runtime distribution gate for every pull request and every push to
   `main`.
2. Build the exact source SHA from the explicit allow-list; verify required
   files, forbidden-path absence, secret boundaries, size policy, compilation,
   plugin loading, and the packaged behavior contracts.
3. Compare the generated tree with the current `runtime` tree. If identical,
   finish as a no-op.
4. If content changed, publish that exact tree to one uniquely named temporary
   candidate branch.
5. Before `runtime` changes, install the candidate with the AstrBot 4.26.1 and
   4.27.2 native updaters through both `repo_branch` and `download_url`.
6. Serialize publication, reject a gate whose source is no longer the current
   `main`, and promote only the candidate commit using an exact
   `force-with-lease` against the previously observed `runtime` SHA.
7. After promotion, block the same publication run on the same four-cell native
   installer matrix against the real `runtime` branch and archive.
8. Delete only the unchanged temporary candidate ref created by that run.
9. Keep external marketplace refresh and real Windows Store observations
   separate; repository success cannot assert those external states.

Publication must never mutate `runtime` first and use a later validation as
permission for the already-visible state. A successful development checkout or
unrelated CI run is not evidence that a distribution artifact is safe or
installable.

## Repository/source binding

AstrBot officially accepts GitHub repository URLs with `/tree/{branch}` for plugin-market `repo` values. This project therefore binds marketplace/runtime installation to the stable `runtime` branch while keeping `main` as the development branch.

The `runtime` branch is generated. It must not become the place where development decisions, tests, or documentation are authored.
