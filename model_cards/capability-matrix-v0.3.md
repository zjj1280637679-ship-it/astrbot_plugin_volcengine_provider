# Seedance Exact-Model Capability Matrix — v0.3

This matrix is a routing/knowledge summary, not a marketing comparison.

Evidence labels:

- `E2E`: exact model + current account + current API path completed end to end.
- `T`: tested observation inside a bounded request domain.
- `D`: provider documentation/product evidence, not exact current-account execution.
- `C`: user control-plane/model-card observation.
- `F`: exact tested route failed.
- `U`: unknown / not established.
- `Q`: repeated quality/reliability evidence; currently none of the visual-quality claims below have Q-level evidence.

## Current exact-model matrix

| Exact model ID | Current route | T2V | Single-image I2V | First+last-frame input | Native audio | Duration evidence | Resolution evidence | Routing status |
|---|---|---|---|---|---|---|---|---|
| `doubao-seedance-1-5-pro-251215` | executable | `E2E` 5s | `E2E` 5s | candidate / not E2E | audio present when field omitted; silent when `generate_audio:false` in tested samples | T2V 5s E2E; user/control-plane condition says no-image T2V may extend to 12s; do **not** propagate 12s to image modes | 720p observed in standardized 5s T2V; not a universal default claim | hard T2V + hard I2V |
| `doubao-seedance-1-0-pro-fast-251015` | executable | `E2E` 5s | `U` exact version | `U` exact version | no audio observed in standardized T2V | 5s E2E; exact maximum `U` | 1080p reported in standardized T2V (`1920x1088` encoded); observation only | hard T2V only |
| `doubao-seedance-1-0-pro-250528` | executable | `E2E` 5s | `E2E` 5s | documented candidate / not E2E | no audio observed in tested T2V/I2V | T2V 5s E2E; I2V 5s E2E; exact maxima `U` by modality | 1080p reported in both tested modes (`1920x1088` encoded); product also positions the model as 1080P-capable | hard T2V + hard I2V |
| `doubao-seedance-1-0-lite-t2v-250428` | current exact route rejected | `F` current route | not this T2V variant by historical product design | not this T2V variant by historical product design | no current task created | historical product evidence: 5s/10s; current route has no executable duration | historical product evidence: 480p/720p; current route has no output | excluded until invalidator changes |

## Important domain boundaries

### Duration is modality-specific

A model-family statement such as `2–12 seconds` must not be copied into every mode. Store duration limits as:

```text
exact_model × modality × input-role/count × output/control conditions
```

Examples:

- `1.5 Pro / T2V / no image`: user/control-plane condition distinguishes this from image-conditioned modes; 12s must not be copied into I2V.
- `1.0 Pro 250528 / T2V`: 5s E2E; maximum currently unknown.
- `1.0 Pro 250528 / single-image I2V`: 5s E2E; maximum currently unknown.
- `Fast 251015 / T2V`: 5s E2E; maximum currently unknown.

Do not spend quota to test every intermediate duration. If maximum duration becomes load-bearing, first seek exact provider documentation; if still unresolved, test only the claimed boundary value with an RCIE audit.

### Resolution is not yet an explicit control claim

Current standardized observations:

- 1.5 Pro: returned `720p` in the D-002 T2V sample.
- Fast 251015: returned `1080p` in the D-002 T2V sample.
- Pro 250528: returned `1080p` in D-003 T2V and D-006 I2V.

These requests did not explicitly isolate a resolution control. Treat the values as observed service/model defaults inside those request domains, not as universal defaults or quality rankings.

### I2V is exact-version specific

Current hard I2V edges:

```text
1.5 Pro 251215      → single-image I2V E2E
1.0 Pro 250528      → single-image I2V E2E
Fast 251015         → unknown exact version
Lite T2V 250428     → not the historical I2V variant; current T2V route rejected anyway
```

Do not inherit Pro Fast 250610 capability descriptions into Fast 251015.

### Continuous-video chaining

The Ark task API documents `return_last_frame`, which returns a PNG final frame for continuity workflows. This API-surface capability is distinct from explicit first+last-frame **input** role support.

Current safe continuity path:

```text
completed video
→ return_last_frame PNG (documented task API)
→ next task uses the already E2E single-image I2V path
```

Explicit first+last-frame role semantics remain a separate model/modal capability until proven.

## Historical Lite context

Seedance 1.0 Lite launch material described Lite video generation at 5s/10s and 480p/720p. A later official Lake AI Service notice listed Lite T2V 250428 and Lite I2V 250428 for discontinuation in that LAS service scope with Seedance 1.5 Pro as replacement.

The current Ark inference test returned `InvalidEndpointOrModel.NotFound`, whose provider message combines at least two causes: exact model/endpoint unavailable **or** current account lacks access.

Therefore:

- historical Lite capability remains a historical fact;
- current Ark executability is false for the tested exact route;
- LAS retirement is supporting context, not a logically unique cause of the Ark 404.

## Prompt-guide status

Volcano Engine currently publishes an official `Seedance 1.0` prompt guide (page updated 2026-07-20). The current retrieval environment confirms the guide exists but cannot parse the JavaScript-rendered detailed body reliably.

Therefore the project does not invent detailed prompt-handle claims from the page title alone. Camera/action/multi-shot wording remains candidate semantic guidance until directly retrieved or quality-tested.

## Next-test policy

No additional generation is justified merely to make the cards look complete.

A new probe requires all of:

1. the unknown changes an actual production/routing decision;
2. exact documentation cannot already settle it;
3. the test isolates one meaningful unknown;
4. existing deterministic evidence is not being redundantly re-proven;
5. Rights–Capability–Intent–Effect audit passes.

Likely future load-bearing probes, only when needed:

- exact Fast 251015 single-image I2V;
- exact duration boundary for a selected model+modality;
- explicit first+last-frame input roles;
- explicit audio enable semantics if a task requires native sound;
- repeated Q-level quality comparison between 1.5 Pro and Pro 250528 for I2V identity/motion/camera adherence.
