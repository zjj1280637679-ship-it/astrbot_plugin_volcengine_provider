# ADR-0001: Provider is not the model-capability authority

## Status

Accepted for 0.1.15.

## Context

An early design direction treated provider/model identity as enough information to pre-fill model capability state. That appears convenient for known first-party models, but it fails as a general provider-plugin rule.

Volcengine Ark can serve first-party Doubao/Seed models and third-party/open models. Model aliases, serving revisions, account/region availability, and future model changes can all invalidate a plugin-local static capability map.

## Decision

The provider plugin owns protocol adaptation and can expose the ceiling of request forms that the adapter knows how to express.

It does not generate permanent model capability facts from a bare model ID, model prefix, brand, or provider membership.

Future automatic discovery is allowed when it has a defined evidence/source/lifetime/scope contract. This ADR rejects unscoped inference, not future technology.

## Rejected alternative

```text
model_id -> static capability table -> AstrBot model capability
```

Counterexamples:

- the same model family may be served through different platforms;
- third-party/open models share the same provider platform as first-party models;
- model and serving behavior can change after plugin release;
- absence of a capability today does not justify a permanent negative claim.

## Consequences

- Agent Plan model-name discovery remains useful without a capability-prior table.
- ordinary Ark runtime feedback can be translated for current display without becoming permanent global truth.
- user configuration controls whether a request path is attempted where the plugin needs an explicit transport switch.
- future capability discovery must declare what kind of information it is and what authority it has.
