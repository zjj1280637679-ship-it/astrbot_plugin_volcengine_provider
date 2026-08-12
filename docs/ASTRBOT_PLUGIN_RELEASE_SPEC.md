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

## 7. Artifact gates

Before a marketplace-visible version is considered released, the generated runtime package must pass all of these gates:

- manifest-only file inventory;
- required metadata/entry files present;
- no forbidden development paths;
- no high-confidence secret patterns;
- package size within policy;
- all packaged Python files compile;
- runtime package loads against supported AstrBot versions;
- actual `runtime` branch/archive can be inspected as an AstrBot plugin;
- store/source metadata version equals runtime `metadata.yaml.version`.

## 8. Update invariant

A version update means:

```text
main development state advances
        +
runtime branch is regenerated from that validated state
        +
marketplace source points to runtime
        +
version metadata matches
```

Adding development files to `main` must not change the contents or size of `runtime` unless those files become explicitly necessary for execution.
