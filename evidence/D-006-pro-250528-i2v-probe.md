# D-006 — doubao-seedance-1-0-pro-250528 Exact Single-Image I2V Probe

## Question

Can the exact model `doubao-seedance-1-0-pro-250528`, under the current account/API key, accept the already verified public GitHub reference image transport plus text and complete a 5-second 16:9 image-to-video task?

This was load-bearing because the executable model graph previously had only one E2E I2V edge: 1.5 Pro.

## Request

Reference image:

```text
https://raw.githubusercontent.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/main/assets/seedance_test/blond_mma_reference_upload_test.jpg
```

Request body intentionally omitted top-level duration/resolution/audio controls:

```json
{
  "model": "doubao-seedance-1-0-pro-250528",
  "content": [
    {
      "type": "text",
      "text": "Keep the same adult blond muscular MMA fighter and the same octagon setting from the reference image. First-person POV close combat-sports training: he advances toward the camera, throws one controlled jab-cross combination, then resets his guard. Natural body mechanics, subtle sweat under overhead lights, cinematic photorealism, no blood, no visible injury. --ratio 16:9 --dur 5"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "<reference URL>"
      }
    }
  ]
}
```

Before task creation, the GitHub runner independently fetched the reference URL and verified that it returned an image with nontrivial byte size. This separates reference-transport failure from model/API failure.

## Core task result

- create HTTP status: `200`
- task id: `cgt-20260812060332-2zpmv`
- final state: `succeeded`
- poll count: `7`
- workflow-measured wall time: `81.59135794639587 s`
- usage: `246840` completion/total tokens
- reported resolution: `1080p`
- ratio: `16:9`
- duration: `5`
- fps: `24`
- draft: `false`
- output format: `mp4`
- service-selected seed: `85153`
- downloaded MP4 bytes recorded by workflow: `9917692`

Local deterministic inspection after Artifact retrieval:

- H.264 video stream only
- encoded dimensions: `1920x1088`
- 24 fps
- duration: `5.041667 s`
- file size: `9917692` bytes
- no audio stream

## Hard conclusion

The exact current path:

```text
public single image URL + text
→ doubao-seedance-1-0-pro-250528
→ Ark asynchronous task
→ succeeded
→ downloadable MP4
```

is **E2E verified** in the current account.

This upgrades Pro 250528 single-image I2V from `documented_candidate` to an executable edge.

## Sample-level visual observation — not a reliability claim

A no-cost frame review of this single output shows that the generated video visibly retained several high-level reference properties:

- adult blond male fighter;
- muscular/shirtless appearance;
- octagon/MMA setting;
- close frontal/POV-style combat composition;
- guard/punch/guard-like action sequence.

It also shows detail drift in this one sample, including changes in glove/wrist colors and some face/environment details.

Therefore:

- reference conditioning is visibly reachable in this sample;
- exact identity/detail consistency reliability is **not established**;
- this one sample must not be used to rank Pro 250528 against 1.5 Pro on I2V quality.

## What this experiment does NOT establish

- stable identity-consistency rate;
- Pro 250528 superiority/inferiority versus 1.5 Pro;
- first+last-frame support;
- audio support;
- universal 1080p or 246840-token law;
- stable latency;
- effectiveness of the phrases `Keep the same...`, `POV`, or other semantic handles as causal factors.

The reference itself, service-selected random seed, model behavior and prompt wording are not independently isolated.

## Epistemic classification

- Pro 250528 exact single-image I2V executability: `conditional_deterministic`, evidence `E2E`.
- observed 1080p / 246840 tokens / no-audio result under this request: `T` observation inside tested domain.
- visible reference-property retention: single-sample reachability observation.
- identity/detail consistency quality: probabilistic, no `Q` evidence.

## Strategy consequence

The project now has two E2E single-image I2V routes:

1. `doubao-seedance-1-5-pro-251215`
2. `doubao-seedance-1-0-pro-250528`

This materially enables model fallback/routing without introducing a new infrastructure subsystem.

Quality-based routing between those two models remains unjustified until a controlled repeated benchmark becomes load-bearing.
