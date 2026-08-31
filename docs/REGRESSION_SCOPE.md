# Regression Scope

## Purpose

This document answers one release question: **which historical evidence must be re-run after a change, and which evidence remains valid unless its dependency path changed?**

The goal is to avoid both under-testing and work explosion.

## Change-to-test map

| Changed area | Required validation | Full QQ media rerun? |
|---|---|---|
| `metadata/`, dynamic `/models` feedback | feedback-presence, isolation, no-global-persistence tests; real `/models` attribution when needed | No, unless media behavior also changed |
| `capabilities/`, migration | migration precedence, foreign-provider isolation, save-boundary tests | No, unless transport semantics changed |
| Dashboard bridge / schema | service-path tests; coarse real Dashboard reachability; UI evidence collection | No |
| `adapters/audio.py` or audio request hook | audio unit/integration regression plus QQ-equivalent audio chain | **Yes** |
| `adapters/video.py` or trusted attachment hook | video trusted-boundary regression plus QQ-equivalent video chain | **Yes** |
| `adapters/image.py` or image limit configuration | byte threshold, longest edge, no-upscale/no-trigger preservation, and metadata-field preservation | No, unless AstrBot's image representation changes |
| AstrBot `MediaResolver` contract/version used by media adapters | compatibility regression using actual host media representation | **Yes** for affected modality |
| Ark `input_audio` / `video_url` contract | raw-vs-plugin protocol attribution plus QQ-equivalent path | **Yes** for affected modality |
| Provider routing/retry/fallback code | normally forbidden plugin ownership change; requires explicit architecture decision | Depends on approved ownership change |
| Documentation / explanatory JSON only | link/consistency review | No |

## Protected historical assets

Historical QQ-oriented audio/video results listed in `docs/TEST_HISTORY.md` remain part of the release evidence set until an impact edge invalidates them. "Not re-run" is not the same as "not validated".

This rule is deliberately narrower than claiming permanent correctness: upstream behavior, AstrBot versions, and QQ/NapCat behavior can change. When one of those relevant dependencies changes, the historical evidence becomes a baseline to reproduce rather than a substitute for a new run.

## Non-equivalent fixtures

Do not use a convenient fixture to silently redefine the product interface.

Examples:

- a generated PCM WAV sent directly to a Provider is not a substitute for a QQ Silk/AMR event flowing through AstrBot;
- a raw MP4/data URL sent directly to Ark is not a substitute for AstrBot's trusted current-request video attachment representation;
- a browser DOM selector is not a substitute for proving the Dashboard service/config path.

A failing non-equivalent fixture should first be classified as a test-scope mismatch. Production code may be changed only after evidence shows that the real owned interface is wrong.

## Release decision rule

A release is blocked when a changed layer lacks evidence at the level required by its ownership, or when impact analysis reaches a historically validated product path that has not been revalidated.

A release is **not** blocked merely because every historical E2E was not repeated after unrelated metadata, documentation, or test-harness changes.
