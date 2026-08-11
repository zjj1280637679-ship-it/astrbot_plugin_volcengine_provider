# Engineering Methodology

## Purpose

This project must not turn tests, UI observations, or historical implementation choices into self-justifying truth. Engineering work proceeds by separating **conditions, observations, evidence, inference, decision, and action**.

## Epistemic pipeline

Every non-trivial change should be expressible as:

```text
Objective condition
  -> Observation
  -> Evidence level
  -> Inference with stated uncertainty
  -> Counterexample search
  -> Decision
  -> Narrow implementation
  -> Re-test
  -> Record newly learned condition
```

A later stage may not silently rewrite an earlier stage. In particular:

- observation is not capability truth;
- a passing unit test is not product-path proof;
- a screenshot is not runtime proof;
- an upstream rejection is not automatically a permanent model property;
- an implementation convenience is not an ownership boundary.

## Four mandatory questions before strategy expansion

1. **Objective condition** — what has actually been observed in AstrBot, Volcengine, QQ/NapCat, or the current repository?
2. **Expected outcome** — what user-visible or protocol-visible behavior is required?
3. **Current strategy** — which layer owns the behavior today, and what native mechanism carries it?
4. **Counterexample** — what legitimate present or future path would this rule break if generalized?

If question 1 is unanswered, investigate before implementing. If question 4 has a plausible counterexample, narrow the rule before implementing.

## Interface existence rule

A flow diagram is not a proof of reachability. Each arrow must be backed by one of:

- an AstrBot-native API/service/component already used by the host;
- a Volcengine-documented or runtime-observed API;
- a repository-owned callable with a regression test;
- a real user/UI path observed in the running Dashboard.

If an arrow is only inferred from code shape or naming, mark it as an assumption and run a minimal existence experiment before building automation around it.

## Prefer precedent before invention

Before adding a new framework-side mechanism, inspect at least one mature precedent when available:

1. AstrBot's own implementation/test path first;
2. an adjacent AstrBot provider with similar lifecycle second;
3. external projects only when the host has no precedent.

Do not add a plugin-side control plane merely because the host path is inconvenient to discover.

## Bounded work rule

Avoid Cartesian-product test plans unless every dimension is load-bearing. Reduce dimensions by ownership:

- plugin contracts test plugin-owned semantics;
- AstrBot integration tests host boundary compatibility;
- real Volcengine tests runtime protocol behavior;
- UI collection records presentation evidence.

Do not multiply provider x version x modality x UI-state when a lower-level invariant can prove several combinations at once.

## Failure attribution loop

For every failure, record:

```text
symptom
-> failing layer
-> preconditions
-> what the failure proves
-> what it does NOT prove
-> whether it generalizes
-> minimal corrective action
```

A repeated failure in a harness must first update the harness model. Production code changes require evidence that the production path is implicated.

## Automation loop

Routine work should continue automatically through:

1. observe current state;
2. classify evidence level;
3. search host precedent;
4. select the narrowest executable path;
5. implement one bounded change;
6. run the narrowest relevant test;
7. run integration/regression tests if the boundary changed;
8. update project state when a new objective condition is learned;
9. continue until the active acceptance target is met.

Stop only when a decision would transfer ownership between AstrBot, this plugin, the user, and the upstream provider/model, or when two legitimate strategies have materially different product semantics.

## UI policy

UI is a presentation environment, not a stable protocol. Browser automation may prove reachability of coarse host surfaces such as login and the Provider page, but layout review is primarily evidence collection:

- screenshots;
- visible semantic text;
- sanitized DOM/layout summaries;
- configuration snapshots.

Selector churn, welcome overlays, Vuetify wrapper changes, or display-label changes must not be attributed to the plugin without independent evidence.

## Runtime policy

Runtime conclusions must identify provenance:

- local input/media transport;
- AstrBot request assembly;
- provider adapter;
- upstream provider response;
- model response.

Only evidence from the relevant layer may justify changing that layer.
