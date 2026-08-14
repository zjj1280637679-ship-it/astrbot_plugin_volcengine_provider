# 0.1.23 robust Video UI candidate

Goal: preserve the cumulative 0.1.16-0.1.22 feature set while making the model-card Video capability resilient when the provider-dialog JavaScript adaptation is stale, cached, or no longer structurally matchable.

Design priority for this candidate:

1. Ark / Agent Plan must have a usable per-model Video control.
2. Saved state and request behavior must remain per-card and consistent.
3. Existing advanced model fields, media behavior, migration and endpoint isolation must remain unchanged.
4. Foreign-provider visual pollution is undesirable but is a bounded fallback side effect; it is less severe than completely losing the Video control. Runtime ownership must still remain Volcengine-only.

The known-good 0.1.22 private-clone bridge remains the preferred UI path. This candidate may add a shared-schema fallback only as a resilience layer and must retain the private bridge so compatible fresh Dashboards remain isolated.
