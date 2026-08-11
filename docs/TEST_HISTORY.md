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

## Revalidation rules

Historical success is reusable evidence when the conditions relevant to that evidence have not changed. It is not a timeless guarantee, but it also must not be erased merely because a later release did not re-run the same expensive or environment-specific path.

A full QQ-equivalent media rerun is required when one or more of these change materially:

- `adapters/audio.py` or the audio hook that feeds it;
- `adapters/video.py` or the trusted-video marker/attachment hook;
- AstrBot `MediaResolver` / media request contract used by the plugin;
- the Ark `input_audio` or `video_url` payload contract;
- QQ/NapCat/OneBot event or attachment semantics relied upon by the path.

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

Production code must not be broadened merely to make a non-equivalent raw media fixture pass. A green raw-provider test can coexist with a broken QQ path, and a red raw-provider test can coexist with an unchanged, historically validated QQ path if the test conditions differ.