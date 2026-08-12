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

- The Source selector save contract succeeds through the real AstrBot service matrix on 4.26.1 and 4.27.2: **L3 host integration evidence**.
- The 2026-08-12 real AstrBot 4.27.2 Dashboard DOM run showed one master per Ark/Plan Source, selectors scoped to their own 2/1 cards, hide/reopen selection preservation with zero API requests, 0/0 controls on foreign Source, no canonical/retired/new video fields in any generic model dialog, and `pageErrors=[]`: **L4 presentation evidence**. The L3 matrix did not substitute for this observation.
- Ark accepts a request containing `video_url`: **L5 upstream runtime evidence**.
- A QQ video reaches Ark and returns a useful model response: **L6 full-path evidence**.

None of these alone should be rewritten as `model supports video forever`.
