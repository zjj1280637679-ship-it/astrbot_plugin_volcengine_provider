# Knowledge Boundary

## Purpose

This document defines the difference between receiving information, interacting with a system, collecting evidence, and making a judgment. The plugin must not promote limited observations into unrestricted conclusions.

## Core rule

**Information availability does not imply judgment authority.**

```text
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

Each transition requires additional conditions. A lower layer may be perfectly functional while still lacking the information or authority required by a higher layer.

## Interaction is not judgment

A successful interaction proves only that a specific path worked under specific conditions.

Examples:

- a request succeeding does not prove permanent model capability;
- a request failing does not prove permanent model incapability;
- a UI field existing does not prove a model supports the feature;
- a model rejecting audio after receiving a valid payload is different from audio never reaching the model;
- a raw Ark request succeeding does not prove the QQ/NapCat/AstrBot product path works.

## Feedback semantics

Runtime feedback is:

- current;
- source-bound;
- time-dependent;
- evidence for an observed interaction.

Runtime feedback is not:

- a permanent model capability database;
- a replacement for upstream documentation;
- permission for automatic behavior changes;
- authority to override user configuration or AstrBot routing.

Unknown or missing feedback remains unknown. Explicit `false`, explicit empty lists, and explicit `0` are observations when the current source actually returned them, but they still remain scoped to that observation.

## Provider responsibility boundary

Provider adapters may:

- translate protocol formats;
- send requests;
- expose current observations;
- identify whether a failure happened before or after an upstream request was formed.

Provider adapters must not:

- become model capability authorities;
- own fallback policy;
- replace AstrBot lifecycle management;
- infer user intent from incomplete signals;
- convert historical success or failure into a timeless runtime rule.

## QQ media boundary

For QQ audio/video features, the real product path is:

```text
QQ event
 ↓
NapCat / OneBot
 ↓
AstrBot media lifecycle / MediaResolver
 ↓
Adapter normalization / trusted attachment translation
 ↓
Provider request
 ↓
Model/provider response
```

A raw provider API test can validate the downstream Ark protocol and help attribute failures, but it cannot replace a QQ-compatible end-to-end test. Conversely, a non-QQ-equivalent synthetic fixture failing does not invalidate an unchanged QQ path that was previously validated.

## Failure attribution

Failures should be classified before conclusions are made:

- **input transport failure**: the request did not validly reach the model/provider request layer;
- **upstream/provider rejection**: the provider/model received the request and rejected it;
- **host integration failure**: AstrBot lifecycle, registration, configuration, or media integration failed;
- **test-harness failure**: the automation failed to reproduce the real interface even though the product path may remain healthy.

The project must not collapse these into a single `model unsupported` conclusion.

## Decision discipline

Before changing production behavior from a test or runtime result, answer:

1. What exactly was observed?
2. Which interface carried the observation?
3. What conditions were present?
4. What does the observation prove?
5. What does it not prove?
6. Is the proposed rule valid for a legitimate counterexample?
7. Who has authority to make the resulting decision: user, AstrBot, plugin adapter, or upstream provider?

If those questions cannot be answered, collect better evidence instead of adding a stronger runtime rule.