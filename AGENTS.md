# AI / Agent Project Entry Point

`docs/PROJECT_STATE.json` is the only HOT/current release-state authority. Read it before README history, tests, PR text, branch names, or old commits.

## Project identity

This repository implements two Volcengine Ark chat providers for AstrBot: ordinary Ark API and Agent Plan. It adapts Volcengine request/media details to AstrBot's existing provider lifecycle. It does not own AstrBot routing, fallback, retries, or a second global model-capability database.

## Branch discipline: exactly one durable truth

`main` is the only durable development, installation, version, and marketplace truth.

- A temporary PR branch may exist only while a concrete change is being reviewed and validated.
- No permanent runtime branch, generated publication branch, version branch, rollback branch, candidate branch, or archive branch is allowed.
- A non-`main` branch must never appear in `metadata.yaml.repo`, README installation instructions, marketplace metadata, or release automation as an installation source.
- After a release is merged, stale branch refs must be deleted when possible or at minimum collapsed to the exact `main` release commit so they cannot carry a different plugin tree or version.
- Failed candidates are stopped, not preserved as alternate live trees. Git history is sufficient historical evidence.

Do not recreate a second publication pipeline even if it seems safer. The repository root on `main` must itself be the complete AstrBot plugin.

## Release truth is user-visible behavior, not code cleanliness

A release is **not successful** merely because Python compiles, unit tests pass, Git has no conflicts, a provider loads, or a Dashboard bridge installs without raising an exception.

For any release touching the model-card UI or release infrastructure, the blocking acceptance is the real running AstrBot Dashboard contract:

1. Create a Volcengine Ark model card in the actual Dashboard.
2. Its native `modalities` row contains exactly one `视频 / Video` checkbox.
3. Click the visible Video label like a user and observe the checkbox become checked.
4. Save, close, reopen, and verify Video remains checked.
5. Repeat for Agent Plan.
6. Confirm the same model card exposes `custom_extra_body` plus the Volcengine request rows: Video Quality, Thinking Mode, Reasoning Effort, Temperature, Top P, Max Output Tokens, Stop Sequences, Frequency Penalty, Presence Penalty.
7. Edit and save the request rows; reopen and verify persistence.
8. Restart the real AstrBot process and verify the owned card still shows a checked Video option.
9. Verify foreign Provider cards have no plugin Video or `volcengine_*` rows.
10. Uninstall the plugin, restart AstrBot, and verify no plugin-owned public UI residue remains.

The current release matrix must include the currently supported verified hosts named in `docs/PROJECT_STATE.json`. A new AstrBot Provider-WebUI generation must be added before claiming compatibility with it.

## Model-card invariant

Video belongs to the **single owned model card's native `modalities` checklist**, beside AstrBot's own Text/Image/Audio/Tool options. It is not a Provider Source master switch, source-level selector, hidden boolean presented as success, or a global fifth modality.

The shared backend schema cannot safely expose Video globally. The implementation may adapt only a concrete model dialog after its `provider_source_id` resolves to one of this plugin's owned Source types. Foreign Provider cards must remain untouched.

Saved `modalities` membership is the current UI truth for video transport. Request-time video conversion follows that saved value. Plugin unload must restore the host boundary.

See `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md` for the permanent product contract.

## Request-field invariant

The owned model card must preserve AstrBot's native `custom_extra_body` row and may additionally expose the plugin's typed per-card request fields. Empty typed fields do not override `custom_extra_body` or platform defaults. Explicit plugin rows are validated at save time and apply after `custom_extra_body` merge by design.

Do not remove those rows merely because the provider can technically send requests without them; their actual model-card visibility and persistence are part of the release acceptance.

## Knowledge discipline

- Current state: `docs/PROJECT_STATE.json`.
- Current release policy: `docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md`.
- Current model-card contract: `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`.
- Historical release summary: `CHANGELOG.md` and Git history.
- Do not create `docs/archive/` state snapshots for failed candidates. They become misleading action-driving context for future AI.
- Versioned regression helper filenames may exist as implementation history, but they are never version authority. Active CI must enter through version-neutral current contract entrypoints.

## Ownership boundaries

- Adapter capability means the plugin can express/transport a request shape; it is not permanent proof that a model supports it.
- Missing upstream feedback is not `false`.
- A local media/transport failure is not evidence that the model lacks the modality.
- A raw provider API result is downstream protocol evidence, not proof of the complete QQ/NapCat/AstrBot path.
- AstrBot owns routing, retry, fallback, provider lifecycle, and installation.
- Provider-specific UI/config fields must not leak into foreign providers.
- Secrets, private config, account state, chat data, generated artifacts, caches, and local captures never belong in the repository.

## Before changing production code

Identify whether the change touches: provider protocol, media adapters, model-card UI/config, request overrides, lifecycle/unload, release/distribution, or only historical explanation. Then run the smallest deterministic tests **and** every real-browser/lifecycle gate whose user-visible object changed. Never substitute a mocked or static assertion for a required real Dashboard observation.
