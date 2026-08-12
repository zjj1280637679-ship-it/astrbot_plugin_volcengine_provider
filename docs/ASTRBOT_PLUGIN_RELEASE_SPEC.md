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

The manifest version is derived from the packaged `metadata.yaml`. Active
build, candidate, and native-install workflows must compare against that
manifest rather than embedding the current plugin version independently. This
keeps one version bump from leaving a stale validator behind. Versions use an
unsigned three-part numeric format. A changed runtime tree must carry a version
strictly newer than the currently published runtime; an identical tree is a
no-op.

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

The runtime distribution gate runs for every pull request and every push to
`main`. It must validate:

- manifest-only file inventory;
- required metadata/entry files present;
- no forbidden development paths;
- no high-confidence secret patterns;
- package size within policy;
- all packaged Python files compile;
- the package loads against supported AstrBot versions;
- packaged Provider/Dashboard behavior contracts pass.

Publication is serialized and consumes the exact artifact accepted by the
successful `main` push gate. An unchanged runtime tree is a no-op. A changed
tree becomes one uniquely named temporary candidate, which must pass this
native-install matrix before `runtime` changes:

```text
AstrBot 4.26.1 × repo_branch
AstrBot 4.26.1 × download_url
AstrBot 4.27.2 × repo_branch
AstrBot 4.27.2 × download_url
```

The publisher must reject a stale source SHA and update `runtime` only with an
exact lease against the previously observed runtime SHA. After a real
promotion, the same publication run must block on the same four-cell matrix
against the promoted `runtime` branch and archive. Candidate validation
authorizes promotion; the post-promotion matrix verifies the actual
user-facing source and is not a substitute for candidate validation.

## 8. Update invariant

A version update means:

```text
all-PR/main-push runtime gate passes
        +
exact accepted artifact is unchanged and publication ends as a no-op
        OR
changed artifact becomes a uniquely named candidate
        +
candidate passes the four-cell native installer matrix
        +
source is still current and runtime advances with an exact lease
        +
promoted runtime passes the same four-cell matrix
        +
marketplace source points to runtime
        +
version metadata matches
```

Adding development files to `main` must not change the contents or size of `runtime` unless those files become explicitly necessary for execution.
