# AI Modification Rules

## Purpose

This document is a fast safety boundary for AI coding agents and maintainers. It makes the project easier to extend without turning explanatory metadata, test output, or one observed interaction into hidden runtime authority.

## Core rules

### 1. Interaction is not judgment

A component may have enough information to receive, translate, send, or display something without having enough information or authority to decide what that thing means globally.

- A successful request proves only that the observed path worked under the observed conditions.
- A failed request proves only that the observed path failed at some layer until attribution identifies which one.
- A UI badge or `/models` field is current feedback, not permanent model truth.
- Missing feedback is not `false`.

See `docs/KNOWLEDGE_BOUNDARY.md`.

### 2. Provider scope must be preserved

This plugin adapts Volcengine Ark protocol differences. It must not replace AstrBot responsibilities such as:

- conversation lifecycle;
- routing and fallback policy;
- retry policy;
- API-key rotation;
- QQ/NapCat media lifecycle;
- global model capability authority.

### 3. Prefer evidence over assumptions

Before changing behavior, identify:

1. observation;
2. evidence source and lifetime;
3. inference;
4. decision authority;
5. at least one legitimate counterexample.

Do not convert an unverified assumption into runtime behavior.

### 4. Preserve future compatibility

Unknown fields and future modality tokens should be preserved when they carry information. Today's adapter vocabulary must not delete information that a future Ark or AstrBot version may understand.

### 5. Test the product interface at the right layer

Raw provider API tests are useful for Ark protocol attribution, but they do not prove QQ compatibility.

The product media path is approximately:

```text
QQ event
  -> NapCat / OneBot
  -> AstrBot media lifecycle / MediaResolver
  -> Volcengine adapter last mile
  -> Provider request
  -> model/provider response
```

A synthetic WAV or MP4 sent directly to a Provider is not equivalent to a QQ event. A test should not make production code more permissive merely to make a non-equivalent fixture pass.

### 6. Historical validated behavior is evidence, not amnesia

Do not treat "not re-run in this release" as "never worked". Check `docs/TEST_HISTORY.md` and `docs/REGRESSION_SCOPE.md` first. Re-run the full QQ-equivalent media path when the media path, host media contract, or payload contract changes; otherwise use the narrowest regression that covers the changed layer.

## Safe extension pattern

New capabilities should normally add one or more of:

- a new evidence source;
- a new adapter translation;
- a new regression test;
- a new explanatory hook or ADR.

They should not add a parallel lifecycle, hidden capability database, duplicate routing state machine, or plugin-owned fallback policy.

## Program annotations are explanatory hooks

Machine-readable files such as `capabilities/SEMANTICS.json`, `docs/PROJECT_STATE.json`, and `docs/DECISION_INDEX.json` are navigation and explanation aids. Production runtime must not read them as capability truth or control policy unless a future explicit design decision changes that boundary.