# ADR-0002: Feedback is evidence, not permanent truth

## Status

Accepted for 0.1.15.

## Context

AstrBot model cards and provider responses expose useful capability-related feedback, but those surfaces are incomplete and time-dependent. A missing icon or missing field does not prove lack of support. A positive indication does not prove that the complete QQ/NapCat/AstrBot/provider path works.

Persisting old dynamic feedback can also cause stale observations to override newer conditions.

## Decision

Treat dynamic provider/runtime feedback as observation scoped to its source and lifetime.

For ordinary Ark `/models` in 0.1.15, plugin feedback is current-response-only, Source-scoped, single-use, and async-context isolated. It is not persisted by the plugin into global `LLM_METADATAS[model_id]`.

Explicit current values remain information when explicitly present, including `false`, an empty list, and integer `0`. Missing fields remain missing. Unknown future modality tokens are preserved rather than filtered out by today's vocabulary.

## Rejected alternatives

- Missing feedback -> `false`.
- Historical dynamic feedback -> current display truth.
- Bare model ID -> permanent capability prior.
- Positive model feedback -> proof that the complete product path works.

## Consequences

The UI can display current feedback without turning the provider plugin into a capability oracle. Debugging remains able to observe real transport failures instead of having them hidden by an earlier automatic capability verdict.
