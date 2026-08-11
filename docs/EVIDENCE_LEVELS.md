# Evidence Levels

Evidence levels describe what a result can support. They are not a scoring system and must not be promoted silently.

| Level | Evidence | Supports | Does not support |
|---|---|---|---|
| L0 | Design hypothesis | Planning an experiment | Runtime/product conclusions |
| L1 | Code inspection | A path or mechanism exists in source | That the path is reachable or correct |
| L2 | Unit/contract test | Local semantics under controlled inputs | Host integration or upstream behavior |
| L3 | Real AstrBot service/integration execution | Host boundary and lifecycle compatibility | UI reachability or upstream model behavior |
| L4 | Real Dashboard observation | A UI surface/layout was observed in that run | Model capability or end-to-end modality support |
| L5 | Real Volcengine API execution | The tested upstream request/response path worked or failed in that run | Permanent capability truth across models/time/accounts |
| L6 | Complete user-path execution | The tested end-to-end path was reachable in that environment | Universal future behavior |

## Rules

1. Missing evidence never means `false`.
2. Historical evidence never overrides a newer direct observation of the same layer.
3. A higher-numbered level does not automatically settle a different layer. For example, a real UI screenshot cannot override a transport trace, and a real API response cannot prove QQ/NapCat media delivery.
4. Negative evidence must retain time, source, environment, and failure provenance when those details matter.
5. Conclusions in documentation and test reports should state the strongest level actually reached.

## Examples

- `ProviderConfigService.create_provider()` succeeds on AstrBot 4.27.2: **L3 host integration evidence**.
- A screenshot shows the video transport toggle on a model card: **L4 presentation evidence**.
- Ark accepts a request containing `video_url`: **L5 upstream runtime evidence**.
- A QQ video reaches Ark and returns a useful model response: **L6 full-path evidence**.

None of these alone should be rewritten as `model supports video forever`.
