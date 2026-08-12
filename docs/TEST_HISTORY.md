# Test History

This file records important validation evidence and prevents future agents from confusing missing reruns with missing capability.

| Version / period | Area | Evidence | Meaning |
|---|---|---|---|
| 0.1.4 | Video | One 4-second red/blue synthetic video was sent through both ordinary Ark and Agent Plan Chat Completions; both returned HTTP 200 and recognized the color order | The implemented video attachment -> `video_url` path worked under those observed conditions |
| 0.1.9 | QQ audio | A real QQ Tencent Silk voice that previously triggered WAV-format failure was normalized to RIFF/WAVE, 16 kHz, mono, PCM16; the same voice as compliant WAV completed an ordinary Ark Chat Completions request with HTTP 200 | The QQ-oriented audio normalization path and Ark `input_audio` contract were validated under those observed conditions |
| 0.1.13 | Architecture | Responsibility audit removed duplicate key-rotation/retry/media lifecycle logic and retained AstrBot ownership | Provider does not own AstrBot lifecycle |
| 0.1.14 | Compatibility | AstrBot 4.26.1 / 4.27.2 matrix passed, including real synthetic Tencent Silk, trusted video attachment bridge, provider registration and real ordinary Ark text | Host integration remained compatible across the tested host versions |
| 0.1.15 | Capability boundary | Runtime-feedback isolation, migration precedence, foreign-provider isolation and transport-failure provenance regressions passed | Feedback/config transport is not capability authority |
| 0.1.16 RC | Runtime evidence | Real ordinary Ark `/models`, text and image raw-vs-plugin attribution succeeded; current ordinary-Ark credential was rejected by both raw and plugin Agent Plan paths | Current failures can be attributed without automatically blaming plugin code or inventing capability facts |
| 0.1.17 | Distribution boundary | Allow-list runtime build produced a ~195 KB ZIP with 21 runtime files; generated package loaded on AstrBot 4.26.1 and 4.27.2; `runtime` branch archive was published and revalidated; both versions' native plugin updaters successfully installed from the `/tree/runtime` repo source and from a direct runtime ZIP URL | Development repository state is no longer treated as the user package; the chosen runtime branch is actually consumable by the declared compatibility floor and current host |
| 0.1.18 RC (2026-08-12) | Source video UI isolation | The Source save contract passed the real AstrBot 4.26.1 and 4.27.2 service matrix (L3). A separate real 4.27.2 Dashboard DOM run passed L4: Ark/Plan masters were 1/1; their opened selectors were 1/1 and contained only their own 2/1 cards; close hid the selector, reopen preserved selection with 0 API requests; foreign was 0/0; Ark/Plan/foreign generic model dialogs contained 0 canonical, retired temporary, or new temporary video fields; `pageErrors=[]` | The 0.1.18 owned-Source configuration boundary, conditional selector presentation, client-side hide/reopen preservation, and generic-card/foreign isolation worked in the observed host/UI conditions. This does not prove model video capability, Ark runtime acceptance, or the QQ product path |
| 0.1.18 RC (2026-08-12) | 0.1.17 upgrade residue and Source-save rollback | Contract regressions reproduced AstrBot 4.26.1 live-schema residue and proved precedence `canonical > exact-Source retired 0.1.17 bool > older per-card > legacy Source bool including false > modalities`; wrong-Source and foreign fields were not promoted, all retired/temporary/wrong-layer fields were removed, and `modalities` stayed unchanged. Focused 4.26.1/4.27.2 regressions reproduced post-save Provider reload failure and Source rename failure; Source/cards, persisted snapshots, manager mirrors, and old-card reload calls returned to the tested pre-call contract while the original error propagated | The 0.1.18 migration preserves only identity-matched intent from the known 4.26.1/0.1.17 upgrade artifact. The tested compensation restores all represented layers; a secondary persistence or old-instance reload failure remains an attached note and no untested layer is claimed restored. These are migration/transaction-boundary results, not model capability or media-path evidence |

## Revalidation rules

Historical success is reusable evidence when the conditions relevant to that evidence have not changed. It is not a timeless guarantee, but it also must not be erased merely because a later release did not re-run the same expensive or environment-specific path.

A full QQ-equivalent media rerun is required when one or more of these change materially:

- `adapters/audio.py` or the audio hook that feeds it;
- `adapters/video.py` or the trusted-video marker/attachment hook;
- AstrBot `MediaResolver` / media request contract used by the plugin;
- the Ark `input_audio` or `video_url` payload contract;
- QQ/NapCat/OneBot event or attachment semantics relied upon by the path.

A distribution-path rerun is required when one or more of these change materially:

- `tools/release/build_runtime_package.py` or the runtime allow-list;
- `metadata.yaml.repo`, `metadata.yaml.version`, plugin identity, or supported AstrBot version range;
- the `runtime` branch publisher;
- AstrBot plugin updater/archive extraction semantics;
- marketplace packaging or download-source semantics.

For changes limited to metadata feedback, Dashboard presentation, migration semantics, documentation, or evidence tooling, run the tests owned by those changed layers and retain the historical QQ media evidence unless impact analysis shows a dependency edge into the media path.

## Important distinction

A raw API fixture is not equivalent to a QQ user event.

```text
raw fixture -> Provider/Ark
```

is useful for downstream protocol attribution, while product compatibility requires the relevant chain:

```text
QQ -> NapCat / OneBot -> AstrBot -> MediaResolver -> plugin adapter -> Ark/model
```

Likewise, a development checkout loading successfully is not equivalent to a user distribution package installing successfully. The generated runtime artifact and its actual AstrBot updater path are separate evidence objects.

Production code must not be broadened merely to make a non-equivalent raw media fixture pass. A green raw-provider test can coexist with a broken QQ path, and a red raw-provider test can coexist with an unchanged, historically validated QQ path if the test conditions differ.
