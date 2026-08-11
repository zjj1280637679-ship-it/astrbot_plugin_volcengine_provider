# Capability and Feedback Boundary

## Why this exists

The project must not collapse several different questions into one boolean:

1. Can the **adapter** express a request shape?
2. Can the **current model endpoint** accept it?
3. Can the **whole product path** deliver it end to end?
4. What did the **current feedback surface** report?

These are related but not equivalent.

## 1. Adapter capability

Adapter capability answers:

> Can this plugin correctly construct/transport this request form for the provider protocol?

Examples:

- build a `video_url` content part;
- serialize normalized audio as Ark `input_audio`;
- forward tool schemas;
- map AstrBot message content into Ark/OpenAI-compatible payloads.

Adapter capability is owned by this plugin.

It does **not** imply that every model exposed by the provider accepts the request.

## 2. Model/endpoint capability

Model capability answers:

> Does the selected model endpoint accept or implement this behavior under the current serving conditions?

This is not safely derivable from a provider name or bare model ID in the general case.

Possible evidence can include:

- official/current provider or model documentation;
- current upstream metadata;
- current runtime acceptance or explicit rejection;
- user knowledge/configuration.

Evidence is not automatically a permanent truth record.

## 3. System capability

System capability answers:

> Can the complete user path achieve the function now?

For media this can include:

`QQ -> NapCat -> AstrBot -> MediaResolver/input normalization -> provider adapter -> Volcengine -> model`

A positive model capability does not guarantee that this complete path works. A broken transport layer must not be reported as a negative model capability.

## 4. Feedback state

Feedback is an observation exposed by the host/provider/runtime. It is not required to enumerate the complete capability set.

Rules:

- no feedback != unsupported;
- no icon != unsupported;
- positive feedback != guaranteed end-to-end product path;
- historical feedback != current feedback;
- current explicit `false`, empty list, or integer `0` is still current information when that field is explicitly present;
- unknown/future tokens should not be destroyed merely because today's plugin does not understand them.

## 5. Configuration state

`volcengine_video_input_enabled` is configuration state:

> attempt/allow video request transport for this model card.

It is not:

- a model capability verdict;
- an official capability assertion;
- a reason to mutate AstrBot `modalities`;
- a router/fallback instruction.

## 6. Failure provenance

Two broad classes must remain distinguishable.

### Input/transport failure before model reach

Examples:

- media resolution/read failure;
- invalid local media normalization;
- failure to construct an Ark media payload.

This is represented as input-transport failure with `reached_model=false` and no capability verdict.

### Upstream/provider/model response

Examples include explicit upstream rejection of a modality or request form. These remain upstream/runtime feedback and continue through AstrBot's native error/fallback machinery.

The plugin should expose provenance but should not copy AstrBot's router to decide what model to try next.

## 7. Authority boundary

| Information | Plugin may produce | Plugin may persist as permanent model truth | May alter AstrBot routing itself |
|---|---:|---:|---:|
| Adapter transport support | yes | n/a | no |
| User transport switch | yes/save | no | no |
| Current Ark `/models` feedback | translate/display | no | no |
| Local failure provenance | yes | no | no |
| Bare model-ID capability guess | no | no | no |
| AstrBot-native metadata | preserve/integrate | not plugin-owned | host-owned |

## 8. Future extension rule

Future mechanisms are allowed. The project is not trying to freeze today's capability knowledge forever.

A future capability/discovery mechanism should make its evidence boundary explicit:

- source,
- observation time/lifetime,
- scope/identity,
- whether the value is configuration, feedback, or a documented assertion,
- what decisions it is permitted to influence.

This provides positive freedom for future technology without allowing an unscoped guess to silently become system truth.
