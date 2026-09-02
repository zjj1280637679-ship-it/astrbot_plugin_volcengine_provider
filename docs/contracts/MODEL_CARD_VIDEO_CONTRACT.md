# Model-card Video Contract

Status: **non-negotiable current product contract**.

This document defines the only acceptable Video UI behavior for `astrbot_plugin_volcengine_provider`. Historical fallback experiments, source-level controls, archive branches and version-specific candidate documents are not authority.

## 1. The object that owns Video

`视频 / Video` belongs to AstrBot's native `modalities` checklist of **one concrete model card**.

For a model card whose `provider_source_id` resolves to either:

- `volcengine_ark_chat_completion`, or
- `volcengine_agent_plan_chat_completion`,

the concrete model dialog may expose exactly one additional native `video` option beside AstrBot's host-owned Text, Image, Audio and Tool use options.

The Provider Source page does not own this switch. There is no source-level master switch, no source-level model selector, and no second user-facing video truth.

## 2. Foreign-provider isolation

OpenAI, xAI, Gemini, DeepSeek and every other foreign Provider model card must remain free of plugin-specific Video injection and `volcengine_*` request rows.

A process-global/shared-schema Video injection that can visually leak to foreign cards is forbidden, even if a later save hook could strip it. “Owned cards keep Video but foreign cards temporarily see it” is not an accepted degradation.

Ownership is resolved from the concrete card's `provider_source_id -> provider_sources[].type`. Endpoint URL, API key shape, model name, brand prefix, DOM position or card order are not valid ownership signals.

## 3. Saved and runtime truth

The concrete owned model card's native `modalities` list is the current UI truth:

- `video` present: Video input is enabled for that card.
- `video` absent: Video input is disabled for that card.

A compatibility mirror such as `volcengine_video_input_enabled` may exist only as a migration/runtime mirror and may not contradict the native owned-card selection.

At request time, only the currently selected owned card's saved Video state controls trusted video attachment conversion to Ark-compatible `video_url` content.

## 4. Request fields are part of the model-card product

An owned Volcengine model card must preserve AstrBot's native `custom_extra_body` row and expose the plugin's typed per-card request rows:

- Video Quality
- Thinking Mode
- Reasoning Effort
- Temperature
- Top P
- Max Output Tokens
- Stop Sequences
- Frequency Penalty
- Presence Penalty

These rows are not optional documentation. Their actual visibility, editability and save/reopen persistence are release requirements.

Empty typed values do not force an override. Explicit typed values are validated and applied with the plugin's documented precedence relative to `custom_extra_body`.

## 5. Current implementation boundary

The current implementation uses three complementary, reversible boundaries:

1. `capabilities/model_fields_bridge.py` contributes hidden shared metadata, projects saved values only onto owned cards, normalizes owned save payloads, and strips plugin fields from foreign cards.
2. `capabilities/dashboard_asset_bridge.py` may adapt a compatible compiled Dashboard asset only when all required concrete-object boundaries are uniquely identified in the same asset. Partial or ambiguous matches fail closed.
3. `capabilities/dashboard_runtime_bridge.py` adapts the already-created visible `AstrBotConfig` model-card component after its concrete `provider_source_id` is available. It reads only Source id/type ownership data from the same-origin provider schema and mutates only owned card-local metadata/data.

No backend shared-schema fallback may add a globally visible Video option. No retired `video_modality_fallback` implementation is part of the product.

All bridges are lifecycle-owned and reversible. Uninstall/release must leave no plugin-owned public UI residue.

## 6. Hard acceptance: observable real UI

A release is successful only when the exact candidate passes the current real-browser contract on every host named in `docs/PROJECT_STATE.json`.

For both Ark and Agent Plan:

1. Open the real AstrBot Dashboard model-create dialog.
2. Observe exactly one native `video` checkbox in `modalities`.
3. Observe that it is initially unchecked for a new card.
4. Click the **visible Video label** as a user would.
5. Observe the actual checkbox become checked.
6. Save the card.
7. Reopen it and observe Video is still checked.
8. Confirm `custom_extra_body` and all typed request rows are visible.
9. Change the typed request rows, save, reopen and verify their values persisted.
10. Reload the Dashboard and verify the saved Video state.
11. Restart the real AstrBot process and verify the saved Video state again.
12. Replace the plugin with the exact same candidate version, restart and verify again.

For foreign cards:

- no plugin Video option;
- no `volcengine_*` request rows;
- no persisted plugin fields.

For uninstall:

- remove the plugin;
- restart AstrBot;
- plugin Source types disappear from public UI;
- a normal foreign card remains free of plugin UI;
- no plugin Dashboard transformation/runtime marker remains served.

## 7. Evidence that does NOT satisfy the contract

None of the following can substitute for the real UI sequence above:

- Python import succeeds;
- syntax/compile succeeds;
- Git merge has no conflicts;
- a unit test or mocked DOM passes;
- a bridge installs without exception;
- source code contains the word `video`;
- metadata says the model supports video;
- a paid/raw video request succeeds while the model-card checkbox is absent;
- a checkbox appears only during creation but not edit/reopen;
- a hidden boolean carries the right value without a visible native checkbox;
- Provider Source controls approximate the per-card behavior.

## 8. Current host matrix

For 0.1.35 the blocking matrix is:

- AstrBot 4.27.3
- AstrBot 4.27.4
- AstrBot 4.28.0-beta.1

The active CI entrypoints are version-neutral:

- `tests/e2e/provider_card_matrix/current_release_ui_contract.py`
- `tests/e2e/provider_card_matrix/current_lifecycle_contract.py`

Versioned helper modules may remain only as internal regression implementation and cannot be cited as current release authority.
