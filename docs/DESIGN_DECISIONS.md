# Design Decisions

Role: durable current constraints. Current release identity lives only in `docs/PROJECT_STATE.json`.

## 1. Scope

The plugin provides two Volcengine Ark chat Provider types for AstrBot: ordinary Ark API and Agent Plan. It adapts provider-specific protocol/media/request details to AstrBot's existing provider lifecycle.

It is not a second router, fallback engine, retry system, provider lifecycle, global capability database or independent Dashboard framework.

## 2. One durable repository truth

`main` is the only durable install/version/publication tree. Required runtime code may not live only in another branch. A temporary PR branch is review-only.

## 3. Concrete owned model card is the UI boundary

AstrBot's shared provider/model schema does not by itself encode “show this field only after this concrete card resolves to one of our Source types.” Therefore provider-specific UI must be scoped after concrete card ownership is known.

Current rule:

- resolve `provider_source_id -> provider_sources[].type`;
- if the type is Ark or Agent Plan owned by this plugin, the private/current card may gain exactly one native `video` modality option and the typed Volcengine request rows;
- foreign cards are unchanged;
- Source-level master switches/selectors are not an acceptable substitute;
- a shared-schema Video fallback that can appear on foreign cards is forbidden.

## 4. Native modalities owns Video state

For an owned card, `modalities` membership is the user-visible Video truth. `volcengine_video_input_enabled` may exist as a compatibility/runtime mirror only.

The plugin does not reinterpret that checkbox as permanent proof that the upstream model supports video; it controls whether the adapter attempts the video transport path for that card.

## 5. Model-card request fields are a product surface

Owned cards preserve AstrBot's `custom_extra_body` and expose the plugin's typed request settings. Empty typed values do not force overrides. Explicit typed values are validated and applied according to `capabilities/model_fields.py`.

Deleting these visible rows while keeping backend request support is a product regression.

## 6. Reversible Dashboard integration

The plugin may use exact compiled-asset and runtime-component adapters only when ownership/boundaries are known and reversible.

- exact compiled-asset transformation must fail closed on partial/ambiguous pattern matches;
- runtime-component adaptation mutates only the currently visible concrete owned card after Source type resolution;
- unload/uninstall restores host methods/assets and must not leave a global fifth modality.

## 7. Capability evidence has scope and lifetime

Ark can serve first-party and third-party/open models. Model names, provider identity, aliases and transient `/models` feedback can drift. Missing feedback is not negative proof, and an observed success/failure does not become permanent global capability truth.

## 8. Failure provenance

Distinguish:

- local media/request construction failure;
- AstrBot host/config/UI failure;
- upstream provider rejection;
- model response;
- test-harness failure.

Do not change production behavior based on a failure attributed to another layer.

## 9. Test hierarchy

For model-card releases:

1. deterministic tests protect code invariants;
2. real built Dashboard automation proves visible create/edit behavior;
3. save/reopen and process restart prove persistence;
4. uninstall proves reversibility;
5. raw provider calls, when needed, prove downstream protocol only;
6. QQ/NapCat end-to-end runs prove the full product path.

A lower layer cannot substitute for an explicit higher-layer acceptance requirement.

## 10. Historical handling

Superseded Source-level Video controls, shared-schema fallbacks, failed candidate branches and old release pipelines are not retained as present-tense current design. Their exact text remains available through Git history. Current docs state only the surviving rule and the lesson that prevents recurrence.
