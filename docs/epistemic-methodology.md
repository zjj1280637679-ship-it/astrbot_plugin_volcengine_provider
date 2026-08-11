# Epistemic Validation Methodology

This document defines the project-level method used before expanding model tests, API integrations, or asset pipelines.

## 1. First principle: a workflow edge is a claim, not a fact

A proposed edge such as `A -> B` must be classified before it is used in architecture.

### Relation classes

- `deterministic_bijective`: A uniquely determines B and B uniquely identifies A within a stated domain.
- `deterministic_forward`: A determines B, but B does not uniquely identify A.
- `conditional_deterministic`: A determines B only if explicit runtime premises remain true (permissions, schema version, quota, service availability, supported input domain, etc.).
- `multi_path_reachable`: multiple distinct paths may reach B. Failure of one path does not imply B is unreachable.
- `probabilistic`: identical or semantically equivalent inputs may produce different outcomes; repeated sampling is required for quality/reliability claims.
- `unknown`: relation has not yet been classified.

## 2. Validation is conditional, not ritual repetition

Do not repeatedly test a relation merely because it is important.

- Deterministic relations are proved/tested once inside the verified domain, then reused until an invalidator fires.
- Conditional deterministic relations are not re-proved every run; only their mutable premises are checked at runtime.
- Probabilistic relations require repeated samples and distributional conclusions.
- Multi-path reachability must be tested path-by-path. Failure of path A never disproves path B unless a shared necessary condition was falsified.
- Reverse inference is permitted only when the relation is known to be injective/bijective over the relevant domain.

## 3. Evidence states

Each claim receives one evidence state:

- `H`: hypothesis only.
- `D`: supported by authoritative documentation.
- `S`: current tool/API schema explicitly supports the operation.
- `T`: the exact operation has been executed successfully in isolation.
- `E2E`: the complete user-relevant path has been executed successfully.
- `Q`: quality/reliability claim supported by repeated benchmark samples.
- `F`: a specific path failed. `F` falsifies only that exact path/claim, not every route to the same outcome.

A claim may carry several supporting evidence items, but its strongest state must not exceed what the evidence proves.

## 4. Domain and invalidators

Every verified claim must state its tested domain and its invalidators.

Example:

```json
{
  "claim": "chat_file_to_github_blob",
  "relation": "conditional_deterministic",
  "status": "T",
  "domain": {
    "input": "readable local JPEG file",
    "encoding": "base64",
    "tested_size_bytes": 336447
  },
  "premises": [
    "GitHub connector exposes create_blob(base64)",
    "repository write permission remains valid"
  ],
  "invalidators": [
    "connector schema changes",
    "repository permission changes",
    "payload exceeds verified or documented limits"
  ]
}
```

Do not expand a conclusion beyond its tested/documented domain.

## 5. Experiment protocol

Every experiment must answer a single falsifiable question whenever practical.

Required fields:

1. `claim_id`
2. `hypothesis`
3. `relation_class`
4. `premises`
5. `independent_variable`
6. `expected_observation`
7. `actual_operation`
8. `observed_result`
9. `what_is_falsified`
10. `what_is_not_falsified`
11. `new_claim_or_update`
12. `invalidators`

Do not use a failed implementation path as evidence that the overall capability is absent.

## 6. Architecture admission rule

A workflow graph has two forms and they must never be confused:

- `possibility_graph`: edges that are merely plausible or documented.
- `executable_graph`: edges backed by sufficient evidence for the intended domain.

Only `T`/`E2E` deterministic or conditional-deterministic edges may be treated as executable infrastructure. `D`/`S` edges remain candidates until tested when they are load-bearing.

Probabilistic model-behavior edges may enter production only with an explicit tolerance/fallback policy.

## 7. Rights-Capability-Intent-Effect review

Every material decision is reviewed in four independent dimensions.

### Rights

- Who authorizes the operation?
- What credentials, repository permissions, asset rights, or user grants are required?
- Is the operation inside the granted scope?
- What event invalidates the grant?

### Capability

- Is the capability documented, schema-supported, tested, or E2E verified?
- What is its relation class?
- What is its verified input domain?
- What failure paths are still open alternatives rather than disproved capabilities?

### Intent

- What user goal does the operation serve?
- Is this operation necessary for the goal, or merely technically possible?
- Is there a lower-cost/lower-risk route with equal effect?

### Effect

- What state changes occur: quota consumption, repository mutation, public asset publication, artifact creation, external service calls, irreversible actions?
- What useful output is produced?
- What risks or cleanup obligations are introduced?

A decision should not proceed merely because Rights and Capability are true; Intent and Effect must also justify it.

## 8. Comparison-before-invention rule

Before introducing a new subsystem (asset gateway, queue, storage bridge, tool protocol, retry engine, etc.), inspect at least one mature comparable architecture and record:

- the problem it solves;
- its control-plane abstraction;
- its asset/resource abstraction;
- its async state model;
- its retry/failure model;
- its security/credential boundary;
- what we can reuse conceptually;
- why a new component is still required, if one is proposed.

No new subsystem should be added only because a single implementation path failed.

## 9. Work-growth brake

When a path fails:

1. Update the exact failed claim.
2. Identify whether failure falsifies a necessary condition or only one implementation path.
3. Enumerate existing alternative paths already exposed by current schemas/tools.
4. Consult comparable implementations before inventing a new subsystem.
5. Choose the minimum experiment that maximizes information gain.

If a proposed next step adds more than one new subsystem at once, stop and decompose it unless the coupling is logically necessary.

## 10. Current project priority

The project must proceed in this order:

1. Establish objective conditions and classify relations.
2. Compare the proposed architecture with mature analogous systems.
3. Run minimal real experiments and perform narrow causal attribution.
4. Apply Rights-Capability-Intent-Effect review to each material decision.
5. Only then expand model capability cards, prompt handles, routing, and quality benchmarks.
