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

1. Run the main gate for every pull request targeting `main` and every push to `main`.
2. Build the runtime tree from the exact triggering source SHA and explicit allow-list.
3. Verify required files, forbidden-path absence, secret boundaries, size policy, compilation, and supported AstrBot loading against the generated artifact.
4. Compare the generated tree with the current `runtime` tree. If identical, finish as a no-op and skip both native-install matrices and promotion.
5. When content changes, publish that exact tree to one unique temporary candidate branch; the candidate is not a marketplace source.
6. Before `runtime` changes, explicitly call the reusable four-cell validator and run AstrBot `4.26.1` and `4.27.2` through both native `repo_branch` and `download_url` installation paths against the candidate.
7. Serialize publication and immediately re-read `origin/main` before promotion. Stop if it has already moved away from the triggering source SHA.
8. Update `runtime` with an exact old-runtime-SHA `force-with-lease` only after all candidate gates pass. Git cannot attach a read-only compare-and-swap to an unchanged `main` ref, so do not describe the main check and runtime update as one atomic transaction. If a main push lands in that final interval, the current candidate is still validated and the new push receives its own gate/publisher; the serialized publisher and runtime lease prevent concurrent overwrite.
9. After a real promotion, the same publish run explicitly calls the same reusable four-cell validator against the promoted `runtime` branch and download URL. This post-promotion check is a blocking publication job.
10. Keep marketplace/real-Windows observations separate: repository validation cannot assert that an external store record has refreshed or that a real Windows Store installation has succeeded.

Publication must never mutate `runtime` first and use later validation as permission for an already-visible state. The post-promotion reusable validator is an identity/regression check of the promoted user source, not a substitute for candidate validation.

A successful development checkout or CI run is not evidence that a distribution artifact is safe or installable.

## Repository/source binding

AstrBot officially accepts GitHub repository URLs with `/tree/{branch}` for plugin-market `repo` values. This project therefore binds marketplace/runtime installation to the stable `runtime` branch while keeping `main` as the development branch.

The `runtime` branch is generated. It must not become the place where development decisions, tests, or documentation are authored.
