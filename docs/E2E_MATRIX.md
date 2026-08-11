# Provider Card × Runtime × Dashboard UI E2E Matrix

## Purpose

Unit tests and service-layer tests can prove that functions behave correctly, but they cannot prove that every legitimate user path is reachable through AstrBot's real provider-card layouts.

This matrix therefore validates three dimensions together:

1. **provider-card/config lifecycle**;
2. **runtime request path with real Volcengine API where appropriate**;
3. **Dashboard UI layout and reachability**.

## Why UI layout is part of correctness

AstrBot does not render every provider as one identical card. Different provider types and Source/model-card flows can use different layouts, sections, conditions, and save paths.

A field can be semantically correct in Python yet still be product-broken if it:

- appears on the wrong provider type;
- appears on the Source card instead of the model card;
- is hidden in a legitimate creation path;
- appears only when editing but not creating;
- moves to the wrong section/advanced group;
- disappears after save/reload;
- contaminates foreign providers.

Therefore the E2E suite must inspect both structure and screenshots.

## Validation dimensions

### Provider/card types

- ordinary Volcengine Ark chat-completion Source;
- Volcengine Agent Plan / agent-runner Source;
- foreign OpenAI-compatible chat provider as an isolation reference;
- at least one non-Volcengine agent-runner reference;
- legacy migrated cards.

### UI lifecycle

For each applicable card:

- create Source;
- edit Source;
- create model/card;
- edit model/card;
- save;
- reload/refresh;
- reopen;
- compare visible fields, groups, order, defaults, and persisted state.

### Runtime input paths

Where supported by the selected real endpoint and test fixture:

- text;
- image;
- audio;
- video transport OFF;
- video transport ON;
- tools;
- combinations that represent legitimate AstrBot input paths.

The suite records upstream acceptance/rejection rather than turning every failure into a permanent capability verdict.

## UI comparison strategy

Use two complementary artifacts.

### Structural snapshot

Capture stable semantic structure rather than pixel positions only:

```json
{
  "provider_type": "chat_completion",
  "source_id": "<test-source>",
  "card_kind": "model",
  "visible_fields": [],
  "hidden_fields": [],
  "field_order": [],
  "groups": {},
  "advanced_default": "collapsed"
}
```

Assertions should cover:

- field ownership;
- field visibility;
- section/group membership;
- relative order where meaningful;
- create/edit parity;
- post-save/reload parity;
- absence of Volcengine UI on foreign providers.

### Browser screenshot

Keep a screenshot for human/AI visual review of layout regressions that a structural snapshot may miss. Screenshot differences are evidence for investigation, not an automatic model-capability conclusion.

## Real Volcengine API path

Use repository secrets; never emit secret values to logs or artifacts.

For ordinary Ark:

1. create/configure the Source through the same service/UI path used by Dashboard;
2. create/select the model card;
3. call real `/models` where available;
4. inspect raw response shape only in sanitized form;
5. verify current-response metadata overlay behavior;
6. issue a minimal real text request;
7. exercise media paths only with explicit fixtures and bounded cost.

For Agent Plan, use its real provider/card path separately rather than assuming ordinary Ark layout or request semantics apply.

## Required invariants

### UI isolation

- Foreign providers never display canonical or temporary Volcengine video fields.
- Temporary UI keys never survive persistence.
- A forged temporary key on a foreign Source cannot create Volcengine state.

### Feedback freshness

- A new `/models` request begins without stale plugin feedback from an older request.
- Current explicit values can replace the same display field for the current Source response.
- Missing fields do not become negative capability claims.
- Current feedback is consumed according to the transient contract.

### Migration

Precedence:

1. current per-card `volcengine_video_input_enabled`;
2. legacy per-card `volcengine_model_video_input`;
3. legacy explicit Source boolean, including `false`;
4. historical `modalities: video` only as the final migration clue.

AstrBot `modalities` itself must remain unchanged.

### Failure provenance

- local media/input transport failure: record transport domain and `reached_model=false`;
- upstream rejection: preserve upstream error path;
- do not add plugin-owned model switching or fallback decisions.

## Matrix result format

A full release report should be able to summarize at least:

```text
Provider/Card Matrix
  Ark Source create/edit            PASS/FAIL
  Ark model create/edit             PASS/FAIL
  Agent Plan Source/card            PASS/FAIL
  Foreign provider isolation        PASS/FAIL
  Legacy migration                  PASS/FAIL

Dashboard
  structural layout snapshots       PASS/FAIL
  create/edit parity                PASS/FAIL
  save/reload parity                PASS/FAIL
  screenshot review                 PASS/FAIL

Real Volcengine API
  ordinary Ark /models              PASS/FAIL/SKIP(reason)
  ordinary Ark text                 PASS/FAIL/SKIP(reason)
  image path                        PASS/FAIL/SKIP(reason)
  audio path                        PASS/FAIL/SKIP(reason)
  video OFF                         PASS/FAIL
  video ON                          PASS/FAIL/SKIP(reason)
  Agent Plan real path              PASS/FAIL/SKIP(reason)
```

## Implementation phases

1. schema/card matrix without secrets;
2. service-level create/save/reload matrix;
3. Dashboard browser automation and layout snapshots;
4. real ordinary Ark API matrix;
5. real Agent Plan path;
6. media-path expansion where fixtures and endpoint support make the test meaningful.

A `SKIP` must include a reason. It must never be silently counted as a pass.
