# AstrBot Plugin Runtime Release Specification

Status: project release policy for `astrbot_plugin_volcengine_provider`.

## 1. Product separation

The GitHub development repository is not the AstrBot installation package.

- Development state optimizes for maintainability, testability, evidence, AI onboarding, and engineering history.
- Runtime state optimizes for minimum sufficient information, installability, portability, privacy, user-facing configuration, and execution reliability.

The release system must transform the former into the latter; it must never simply rename an arbitrary repository archive as a product package, and developers must not evolve `runtime` independently of `main`.

## 2. AstrBot-compatible distribution sources

AstrBot plugin-market records support a GitHub `repo` pointing to a branch using:

`https://github.com/{owner}/{repo}/tree/{branch}`

This project uses the generated stable branch `runtime` for that path.

AstrBot Cloud publication is a second surface. A historical release was observed to freeze the default-branch commit rather than the branch named in `metadata.repo`. The project therefore does not infer Cloud package identity from the metadata URL: before publication, the default-branch export must be exactly equivalent to the allow-list runtime package; after publication, the real frozen Cloud ZIP is an independent external observation.

The installed archive must contain a valid `metadata.yaml` at the plugin archive root (or its single top-level repository directory), with non-empty `name`, `desc`, `version`, and `author` fields.

## 3. Size policy

AstrBot's published plugin-market guidance limits plugin ZIP packages to 16 MB unless maintainers explicitly bypass the limit.

This project uses a stricter default runtime budget of **2 MiB** because its runtime is source code, one logo and small user-facing documents/configuration. Crossing this budget is a review trigger, not an invitation to remove required functionality.

## 4. Runtime manifest

The runtime branch is generated from an explicit allow-list:

```text
metadata.yaml
__init__.py
main.py
providers.py
registry.py
_conf_schema.json
README.md
logo.png
LICENSE
CHANGELOG.md
adapters/*.py
capabilities/*.py
compatibility/*.py
metadata/*.py
```

Runtime root files have concrete consumers:

- `metadata.yaml`: AstrBot discovery and update identity.
- `_conf_schema.json`: AstrBot detects this file before plugin instantiation, creates/updates the plugin config, exposes it in WebUI, and passes the resulting config object into the plugin constructor.
- `README.md`: user-facing documentation for the actual installable branch. Because it is part of the immutable runtime tree, release-state settlement after promotion must not require rewriting it at the same version.
- `CHANGELOG.md`: AstrBot reads the installed file to render the post-update changelog popup.
- `logo.png` / `LICENSE`: runtime identity and license distribution.

The manifest version is derived from the packaged `metadata.yaml`. Active build, candidate, and native-install workflows must compare against that manifest rather than embedding the current plugin version independently. Versions use an unsigned three-part numeric format. A changed runtime tree must carry a version strictly newer than the currently published runtime; an identical tree is a no-op.

## 5. Development-only classes

The following remain excluded even when public in the development repository:

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
.gitignore
```

A future file remains development-only by default. To add it to runtime, the change must identify the runtime consumer/import or user-facing necessity.

`README.md` and `_conf_schema.json` are explicitly **not** development-only. Removing either from the generated package is a release-boundary regression.

## 6. Confidentiality and garbage-information policy

The runtime artifact must not contain information merely because it helped development. In particular it must not distribute:

- CI/CD implementation details;
- internal AI prompts/onboarding;
- debugging or benchmark output that is not part of the user-facing product contract;
- experiment evidence or research data;
- test media or private samples;
- credentials, tokens, secrets, account state, private configuration, or conversation data;
- dead files with no runtime consumer.

Public development material can still be inappropriate for the runtime package: disclosure risk and runtime noise are separate from repository visibility.

## 7. Artifact and promotion gates

The Runtime Distribution Gate runs for every pull request and every push to `main`. It must validate:

- HOT state / metadata / README projection consistency;
- manifest-only file inventory;
- `_conf_schema.json`, `README.md`, `CHANGELOG.md`, metadata and entry files present;
- no forbidden development paths;
- no high-confidence secret patterns;
- package size within policy;
- exported default-branch inventory and bytes equal the allow-list runtime artifact;
- all packaged Python files compile;
- the package loads against supported AstrBot versions;
- packaged Provider, Dashboard and media/cache/context regression contracts pass.

Publication is serialized and consumes the exact artifact accepted by the successful `main` push gate. An unchanged runtime tree is a no-op. A changed tree becomes one uniquely named temporary candidate, which must pass this native-install matrix before `runtime` changes:

```text
AstrBot 4.26.1 × repo_branch
AstrBot 4.26.1 × download_url
AstrBot 4.27.2 × repo_branch
AstrBot 4.27.2 × download_url
```

The publisher must reject a stale source SHA and update `runtime` only with an exact lease against the previously observed runtime SHA. After a real promotion, the same publication run must block on the same four-cell matrix against the promoted `runtime` branch and archive. Candidate validation authorizes promotion; the post-promotion matrix verifies the actual user-facing source and is not a substitute for candidate validation.

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
default-branch export equals generated runtime bytes
        +
version metadata matches
```

Adding development files to `main` must not change the exported package or `runtime` unless those files become explicitly necessary for execution or user configuration.

After publication, changing only HOT development state from “candidate” to “stable” must be possible without mutating any file shipped in the already-published runtime tree. Runtime files are immutable within a version; a real runtime-content change requires a strictly newer version.

## 9. Branch authority

`main` is the only development truth. `runtime` is a generated product surface, not a parallel development branch.

Allowed direction:

```text
main → gate artifact → immutable candidate → runtime
```

Disallowed steady state:

```text
runtime-only feature work
runtime-only version bump
manual runtime fix that is not immediately reconciled into main
```

Emergency observations on `runtime` may inform a repair, but the repair itself must be implemented and validated from `main` before the next publication.
