# AI Modification Rules

`docs/PROJECT_STATE.json` is the only HOT/current release authority. `AGENTS.md` and `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md` define the durable product/release boundaries.

## 1. One durable branch truth

`main` is the only durable development, installation and publication truth. Temporary PR branches are review objects only. Never create a second runtime/generated/version/rollback publication tree.

A failed candidate stays non-releaseable and is fixed or abandoned; it is not promoted merely because a version number exists.

## 2. Observable product behavior beats structural success

For model-card UI work, success means the real AstrBot Dashboard behaves correctly:

- owned Ark and Agent Plan cards each show exactly one native Video checkbox;
- a visible-label click actually checks it;
- save/reopen and real process restart keep it checked;
- `custom_extra_body` and the typed Volcengine request rows are visible;
- request rows persist after save/reopen;
- foreign cards stay clean;
- uninstall removes plugin-owned public UI.

Import, compile, no-conflict, unit-only, mocked DOM or “bridge installed” results cannot substitute for that sequence.

## 3. Keep object ownership exact

- Provider Source identity is used to decide whether a concrete card is owned.
- Video state belongs to the concrete owned card's native `modalities` list.
- Do not build a Source-level Video selector/master switch.
- Do not add a process-global/shared-schema Video fallback that can appear on foreign cards.
- Do not infer ownership from endpoint URL, model name, card order or brand label.

## 4. Preserve request-field product surface

Owned model cards keep AstrBot's native `custom_extra_body` and the plugin's typed request rows. Do not remove those rows merely because a raw request can still be sent.

Empty typed fields preserve platform/custom-body defaults. Explicit typed values are validated and applied according to `capabilities/model_fields.py`.

## 5. Interaction is not permanent capability truth

- Successful interaction proves only the observed path under observed conditions.
- Failure must be attributed to local transport, host, upstream or model before drawing a capability conclusion.
- Missing feedback is not `false`.
- Provider/model names are not permanent capability facts.
- Raw provider API evidence is not proof of the complete QQ/NapCat/AstrBot path.

## 6. Respect host ownership

AstrBot owns provider lifecycle, routing, retry, fallback, provider/source persistence and shared Dashboard rendering. The plugin adapts Volcengine-specific protocol/media behavior and its scoped model-card fields; it must not duplicate AstrBot policy state machines.

## 7. Historical data must not look current

Deep history lives in Git. Current-tree documentation should contain only still-valid constraints and concise release summaries.

When a strategy is superseded or a candidate fails:

- remove/update present-tense instructions that describe it;
- do not create a current-tree archive snapshot that future AI can mistake for active guidance;
- keep the necessary lesson in the higher-version CHANGELOG, Git history or a clearly current rule.

## 8. Secrets and local artifacts

Never commit API keys, credentials, private config, chat/account state, local captures, caches, generated media or CI artifacts. Production modules must not import documentation, governance or tests.
