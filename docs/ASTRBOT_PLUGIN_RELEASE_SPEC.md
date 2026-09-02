# AstrBot Plugin Release Specification

Status: current release policy for `astrbot_plugin_volcengine_provider`.

## 1. One durable publication truth

The default branch `main` is the only durable installation, version and marketplace authority. The root of `main` must always contain a complete AstrBot plugin, including `metadata.yaml`, `main.py`, `_conf_schema.json`, provider/runtime modules, logo, README, CHANGELOG and license.

A temporary PR branch is allowed only as a review object. It must never become an install URL, marketplace source, generated runtime tree, rollback tree or alternate version line. After merge, stale non-main refs must be deleted when tooling permits; if a connector cannot delete a ref, it must be force-collapsed to the exact final `main` release commit so it carries no alternate history, tree or version.

Do not create a second packaging/publishing branch. If `main` is not a complete installable plugin, the release is broken.

Canonical repository URL:

`https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider`

## 2. Version identity

- `metadata.yaml` is the installable checkout version source.
- Every publication uses a strictly newer unsigned three-part version such as `0.1.35`.
- Never rewrite a bad exposed version in place; fix it with a higher version.
- `repo` is always the repository root, never a branch or subdirectory URL.
- README, CHANGELOG and `docs/PROJECT_STATE.json` must describe the same candidate/stable identity.
- Failed candidates are not preserved as alternate live trees. Git history is sufficient for deep audit.

## 3. Release success is a running UI fact

Static checks are necessary but insufficient. A release that compiles but gives users a broken model card is a failed release.

For model-card or release-topology changes, all of the following are blocking:

1. Build the exact AstrBot host Dashboard from source and install that built Dashboard into the exact host runtime.
2. Start AstrBot with the exact plugin candidate checkout.
3. Drive the actual Dashboard with Playwright using normal user-visible controls.
4. On both Volcengine Ark and Agent Plan model cards, observe exactly one native `Video` checkbox in `modalities`.
5. Click the visible Video label; verify the checkbox is checked.
6. Save, close and reopen the model card; verify Video is still checked.
7. Verify the model card visibly contains AstrBot's `custom_extra_body` plus Video Quality, Thinking Mode, Reasoning Effort, Temperature, Top P, Max Output Tokens, Stop Sequences, Frequency Penalty and Presence Penalty.
8. Change the typed request fields, save, reopen and verify their values persisted.
9. Verify foreign OpenAI/xAI/Gemini cards contain no plugin Video or `volcengine_*` rows.
10. Restart the real AstrBot process and verify the owned saved Video checkbox remains checked.
11. Replace the plugin with the exact same candidate version and verify state again.
12. Uninstall the plugin, restart AstrBot, and verify no plugin-owned public UI residue remains.

A passing import, syntax check, unit suite, DOM-free bridge test, or “bridge installed” status cannot replace any required visible browser observation above.

## 4. Host matrix

The current 0.1.35 gate covers:

- AstrBot 4.27.3
- AstrBot 4.27.4
- AstrBot 4.28.0-beta.1, whose Provider WebUI was redesigned

A host is considered verified only when the real Dashboard and required lifecycle jobs pass on that exact candidate SHA. Tested hosts are evidence, not an artificial upper bound on `astrbot_version`.

## 5. Static and deterministic gates

Before browser acceptance, the candidate must also pass:

- `tools/release/check_main_install_source.py`
- `tools/release/check_single_truth.py`
- all top-level deterministic `tests/test_*.py`
- secret/path/size checks already enforced by the main install-source checker

No paid Ark/DeepSeek request is required for a UI/release-topology-only version. Paid provider calls are separate protocol evidence and must not be used to mask a broken UI gate.

## 6. Publication flow

1. Start from the current remote `main`.
2. Create one temporary review branch.
3. Bump to a strictly newer version and mark it `validating`, `releaseable: false` in `docs/PROJECT_STATE.json`.
4. Remove obsolete publication/fallback/failed-state infrastructure from the candidate tree.
5. Open a PR to `main` and run the full three-host real-Dashboard and lifecycle matrix.
6. If any blocking gate fails, fix the same candidate branch or abandon it. Do not declare the version stable and do not create an alternate publication branch.
7. After every blocking gate passes, update the exact candidate to `ready`, `releaseable: true`; rerun every required check on that exact SHA.
8. Merge only that reviewed ready SHA into `main`.
9. Project `docs/PROJECT_STATE.json` and README to stable `0.1.35` on `main`; rerun the stable push gates.
10. Collapse/delete stale non-main refs so none carries an alternate tree/version.
11. A GitHub tag/Release may be added for traceability, but `metadata.yaml` on `main` remains the installation truth.
12. Marketplace approval/indexing is a separate external state and must not be claimed until observed.

## 7. Evidence boundaries

- Real Dashboard checkbox/persistence evidence proves UI/config behavior only; it does not prove every upstream model accepts video.
- Provider API evidence proves the downstream protocol edge only; it does not prove the QQ/NapCat/AstrBot product path.
- Marketplace visibility proves indexing only; it does not replace repository/runtime acceptance.

Each claim must stay at the layer actually observed.
