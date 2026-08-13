# Seedance Objective Conditions — v0.1 (historical pre-probe snapshot)

> **Lifecycle: COLD / non-action-driving.** This file records the conditions that existed before D-002, D-003 and D-006 were executed. It must not be used as current model status or as authorization to rerun paid probes. Current bounded results live in `strategy/executable-model-graph-v0.2.json`; the provider release goal lives only in `docs/PROJECT_STATE.json`.

Purpose: establish what is objectively known before spending generation quota on capability probes.

## Evidence hierarchy for model facts

For **hard runtime facts** such as exact model ID, accepted request schema, model availability, and output lifecycle, use this priority:

1. E2E runtime result in the user's account/context.
2. Current user control-plane/model-card observation.
3. Official Ark API documentation / API Explorer.
4. Volcano Engine developer-community articles as implementation/capability leads only.
5. Third-party examples as hypotheses only.

Reason: official developer-community articles currently contain conflicting historical/version IDs, so they cannot alone establish the exact current model identifier.

## Source conflict discovered

The official Ark CreateContentsGenerationsTasks API documentation uses `doubao-seedance-1-0-pro-250528` as the model example and explicitly supports text plus image inputs. It also documents `return_last_frame` at the task API level.

Different Volcano Engine developer-community articles list different historical IDs for the same product families (for example different Pro/Fast/Lite version suffixes). Therefore:

- product-family capability descriptions from those articles may be useful as hypotheses;
- exact version IDs from community articles are not promoted to executable truth without control-plane/runtime confirmation.

## Exact model IDs supplied for this project

### 1. doubao-seedance-1-5-pro-251215

Hard status:

- Exact ID: `E2E` — successfully used by this project.
- Text-to-video: `E2E`.
- Single-image image-to-video: `E2E`.
- Async task create/poll/download lifecycle: `E2E`.
- MP4 return to ChatGPT through GitHub Artifact: `E2E`.

Candidate capabilities not yet promoted to executable truth:

- first+last-frame generation: official developer-community material reports support, but this exact mode has not yet been executed by this project.
- native audio generation: official developer-community material reports support, but audio has not yet been executed by this project.
- draft mode: reported by a Volcano Engine developer-community implementation; requires direct authoritative/runtime confirmation before use as a hard capability.

### 2. doubao-seedance-1-0-pro-250528

Hard status:

- Exact ID: `D` — present in official Ark video-generation API examples.
- Text/image content structure: `D` at the API level.
- Model-specific T2V/I2V support: developer-community material reports both, but this exact ID has not yet been run in this project.

Important distinction:

The generic video API accepting image input does not logically prove every model ID supports image-to-video. Model-specific capability must be established separately.

Historical pre-probe status: not yet executed. Current bounded result: exact T2V is executable; exact single-image I2V is also executable. See `evidence/D-003-remaining-models-probe.md` and `evidence/D-006-pro-250528-i2v-probe.md`.

### 3. doubao-seedance-1-0-lite-t2v-250428

Hard status:

- Exact ID: supported by current Volcano Engine materials and user model-card observation.
- Product intent: developer-community material consistently describes the T2V variant as text-to-video oriented.
- Current lifecycle note: an official Volcano Engine service-adjustment notice lists the 250428 Lite T2V line for replacement by Seedance 1.5 Pro in the referenced service context. This does not by itself prove the user's Ark entitlement is unavailable; account/runtime context must be distinguished from that notice's service scope.

Historical pre-probe status: `untested`. Current bounded result: this exact route was rejected before task creation with `InvalidEndpointOrModel.NotFound`; the provider response does not distinguish model absence from account entitlement. See `evidence/D-003-remaining-models-probe.md`.

### 4. doubao-seedance-1-0-pro-fast-251015

Hard status:

- Exact ID: `C` (user control-plane/model-card observation).
- Indexed official API/developer materials found so far commonly expose other Pro Fast suffixes (for example 250610), not this exact `251015` identifier.
- Therefore no capability should be inherited from another Fast suffix solely by family name.

Historical pre-probe status: `untested`. Current bounded result: exact minimal T2V is executable; I2V, first/last-frame and exact-version audio remain unproven. See `evidence/D-002-controlled-model-probe.md`.

## API-level facts independent of a particular model's quality

The Ark video task API documents:

- model ID / endpoint selection;
- `content[]` containing text and image input objects;
- asynchronous task creation;
- status lifecycle including queued/running/succeeded/failed;
- optional callback URL;
- optional `return_last_frame`, with the returned last frame available through task query after successful generation.

These are API-surface facts. They do **not** imply that every model supports every possible input combination.

## Management/control-plane limitation discovered

Ark also exposes management APIs such as ListFoundationModels / GetFoundationModelVersion. Official examples use the Volcano Engine open API management plane and HMAC AK/SK-style authentication. The current project secret is the Bearer-style Ark inference API key used successfully on `/api/v3/contents/generations/tasks`.

Therefore the existence of a management API does not imply the current inference secret can query it. Do not build a control-plane discovery workflow until compatible credentials/authorization are actually available.

## Quota claim

User-reported condition:

- each supplied model ID has a daily free allowance of 2,000,000 tokens.

Current evidence level: user/account-context report, not independently queried by this project.

Methodological consequence:

- do not burn generation quota merely to repeatedly prove deterministic capabilities already established;
- use quota only for load-bearing unknowns or probabilistic quality measurements;
- if an authoritative account/control-plane usage source becomes accessible, prefer that over inference-side probing for quota verification.

## Immediate testing policy derived from these facts

Do not run a generic P1–P6 benchmark sweep.

Only run a generation when all are true:

1. the capability is load-bearing for an intended task;
2. authoritative docs/control-plane evidence do not already settle it;
3. the exact model/version matters and cannot safely inherit a family-level claim;
4. the experiment changes one meaningful unknown or measures a genuinely probabilistic quality property;
5. Rights-Capability-Intent-Effect review permits the quota and asset effects.
