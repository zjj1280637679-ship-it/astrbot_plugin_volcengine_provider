# Knowledge Boundary

## Purpose

This document defines the difference between information reception, interaction, evidence, and judgment. The plugin must not promote limited observations into unrestricted conclusions.

## Core rule

Information availability does not imply judgment authority.

```
Information
    ↓
Observation
    ↓
Interaction
    ↓
Evidence
    ↓
Inference
    ↓
Decision
```

Each layer has a narrower responsibility.

## Interaction is not judgment

A successful interaction proves only that a specific path worked under specific conditions.

Examples:

- A request succeeding does not prove permanent model capability.
- A request failing does not prove model incapability.
- A UI field existing does not prove a model supports the feature.

## Feedback semantics

Runtime feedback is:

- current;
- source-bound;
- time-dependent;
- evidence for this observation.

Runtime feedback is not:

- a permanent model capability database;
- a replacement for upstream documentation;
- permission for automatic behavior changes.

## Provider responsibility boundary

Provider adapters may:

- translate protocol formats;
- send requests;
- expose current observations.

Provider adapters must not:

- become model capability authorities;
- own fallback policy;
- replace AstrBot lifecycle management;
- infer user intent from incomplete signals.

## QQ media boundary

For QQ audio/video features, the real product path is:

```
QQ event
 ↓
NapCat / OneBot
 ↓
AstrBot media lifecycle
 ↓
Adapter normalization
 ↓
Provider request
 ↓
Model response
```

A raw provider API test cannot replace a QQ-compatible end-to-end test.

## Failure attribution

Failures should be classified before conclusions are made:

- transport failure: request did not reach the model;
- provider rejection: model/provider received and rejected the request;
- integration failure: host lifecycle or adapter path failed.

The system must not collapse these into a single "model unsupported" conclusion.
