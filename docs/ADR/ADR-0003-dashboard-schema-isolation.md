# ADR-0003: Dashboard schema must isolate provider-owned UI

## Status

Accepted for 0.1.15.

## Context

AstrBot model-card schema is shared. Adding an unconditional Volcengine-specific field to the shared schema can cause that field to appear on unrelated providers. AstrBot provider types also use different Dashboard layouts, so schema visibility is part of product correctness, not merely presentation.

## Decision

Do not expose the canonical `volcengine_video_input_enabled` field as an unconditional shared model-card schema item.

For owned Volcengine Sources, the Dashboard bridge may create a temporary Source-scoped UI key guarded by AstrBot's native `condition` on `provider_source_id`. The key uses a reversible UTF-8-to-hex encoding of the Source ID so identity is not truncated or probabilistically hashed.

At the create/update save boundary, the bridge converts the owned temporary UI value to the canonical model-card transport field and removes the temporary UI key before ProviderManager persistence.

If the host lacks the complete schema/create/update API set needed to preserve this save contract, the UI enhancement is not exposed. Other independently safe bridge hooks may still operate.

## Required invariants

- foreign providers do not display the Volcengine field;
- temporary UI keys do not persist;
- a forged temporary key on a foreign Source cannot create Volcengine state;
- Source/model-card field ownership remains distinct;
- create and edit paths are both tested;
- layout correctness must be checked against real AstrBot Dashboard provider-card layouts, not schema data alone.

## Consequences

The implementation is more explicit than one global schema field, but it avoids cross-provider UI pollution and preserves AstrBot's own rendering model.
