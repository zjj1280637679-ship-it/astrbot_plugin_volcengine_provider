# AstrBot Plugin Runtime Release Specification

Status: project release policy for `astrbot_plugin_volcengine_provider`.

## 1. Product separation

The GitHub development repository is not the AstrBot installation package.

- Development state optimizes for maintainability, testability, evidence, AI onboarding, and engineering history.
- Runtime state optimizes for minimum sufficient information, installability, portability, privacy, and execution reliability.

The release system must transform the former into the latter; it must never simply rename the repository archive as a product package.

## 2. AstrBot-compatible distribution source

AstrBot plugin-market records support a GitHub `repo` pointing to a branch using:

`https://github.com/{owner}/{repo}/tree/{branch}`

AstrBot resolves that branch to a ZIP archive for installation. This project uses the stable branch `runtime` as the marketplace installation source.

The installed archive must contain a valid `metadata.yaml` at the plugin archive root (or its single top-level repository directory), with non-empty `name`, `desc`, `version`, and `author` fields.

## 3. Size policy

AstrBot's published plugin-market guidance limits plugin ZIP packages to 16 MB unless maintainers explicitly bypass the limit.

This project uses a stricter default runtime budget of **2 MiB** because its actual runtime is source code plus one logo. Crossing this budget is a review trigger, not an invitation to delete required functionality.

## 4. Runtime manifest

The runtime branch is generated from an explicit allow-list:

```text
metadata.yaml
__init__.py
main.py
providers.py
registry.py
logo.png
LICENSE
adapters/*.py
capabilities/*.py
compatibility/*.py
metadata/*.py
```

Only files required by Python imports, AstrBot plugin discovery/configuration, runtime UI identity, or licensing belong here.

## 5. Development-only classes

The following are excluded even if public in the development repository:

```text
.github/**
tests/**
docs/**
evidence/**
governance/**
strategy/**
model_cards/**
assets/** test/experiment media
AGENTS.md
ARCHITECTURE.md
CHANGELOG.md
README.md
.gitignore
```

A future file remains development-only by default. To add it to runtime, the change must identify the runtime consumer/import or user-facing necessity.

## 6. Confidentiality and garbage-information policy

The runtime artifact must not contain information merely because it helped development. In particular it must not distribute:

- CI/CD implementation details;
- internal AI prompts/onboarding;
- debugging or benchmark output;
- experiment evidence or research data;
- test media or private samples;
- credentials, tokens, secrets, account state, private configuration, or conversation data;
- dead files with no runtime consumer.

Public development material can still be inappropriate for the runtime package: disclosure risk and runtime noise are separate from repository visibility.

## 7. Artifact and promotion gates

The main gate runs for every pull request targeting `main` and every push to `main`, and publication is serialized. Each publish run builds the exact triggering source SHA, verifies manifest inventory, required files, forbidden-path absence, high-confidence secret patterns, size policy, Python compilation, and supported-AstrBot loading, then compares the generated tree with the current `runtime` tree. If the trees are identical, the run ends as a no-op and skips the pre-promotion matrix, promotion, and post-promotion matrix.

When content changes, the exact tree is published to one unique temporary candidate branch. Before `runtime` changes, the publish run explicitly calls the reusable four-cell validator against that candidate:

```text
AstrBot 4.26.1 × repo_branch
AstrBot 4.26.1 × download_url
AstrBot 4.27.2 × repo_branch
AstrBot 4.27.2 × download_url
```

Immediately before promotion, the workflow re-reads `origin/main` and stops if it has already moved away from the triggering source SHA. It then updates `runtime` with an exact old-runtime-SHA `force-with-lease`. Git cannot express a read-only compare-and-swap for an unchanged `main` ref, so the policy must not claim these are one atomic transaction. If a main push lands in the final update interval, the current candidate remains fully validated and the new push receives its own gate/publisher; publication serialization and the runtime lease prevent concurrent overwrite. After a real promotion, the same publish run explicitly calls the same reusable four-cell validator against the promoted `runtime`; this post-promotion validator is a blocking job and does not authorize a publish that failed candidate validation.

## 8. Update invariant

A version update means:

```text
all-PR/main-push gate passes
        +
exact source SHA produces a runtime tree
        +
identical runtime tree exits as a no-op with both matrices and promotion skipped
        OR
changed tree becomes one unique temporary candidate
        +
candidate passes artifact gates and the reusable four-cell native-install validator
        +
source SHA is still the observed main tip immediately before promotion
        +
runtime changes with an exact old-SHA force-with-lease
        +
the same publish run blocks on the reusable four-cell validator against promoted runtime
        +
marketplace source points to runtime and version metadata matches
```

Adding development files to `main` must not change the contents or size of `runtime` unless those files become explicitly necessary for execution. External AstrBot Store refresh and real Windows Store installation remain separate observations; repository success must not claim them.
