# D-003 Remaining Exact Models Probe — Result and Causal Attribution

## Question

Under the same current account/API key and standardized minimal T2V request used in D-002, are the two remaining supplied exact IDs executable?

- `doubao-seedance-1-0-pro-250528`
- `doubao-seedance-1-0-lite-t2v-250428`

No already-verified 1.5 Pro or Fast model was re-run.

## Controlled request

Both exact IDs received the same text-only request shape:

```json
{
  "model": "<exact model id>",
  "content": [
    {
      "type": "text",
      "text": "Cinematic photorealistic close-up sports training. An adult athletic man shadowboxes in a professional gym, performs one controlled jab-cross combination, then resets his guard. Natural body mechanics, subtle sweat under overhead lights, stable readable motion, no blood, no injury. --ratio 16:9 --dur 5"
    }
  ]
}
```

No top-level duration, resolution, audio or draft control was supplied.

## Result A — doubao-seedance-1-0-pro-250528

Generation result:

- create HTTP status: `200`
- task id: `cgt-20260812054923-q2v2b`
- final task state: `succeeded`
- poll count: `7`
- workflow-measured generation/download wall time: `70.75958704948425 s`
- reported usage: `246840` completion/total tokens
- reported resolution: `1080p`
- reported ratio: `16:9`
- reported duration: `5`
- reported fps: `24`
- reported draft: `false`
- output format: `mp4`
- downloaded MP4 bytes: `8440389`
- service-selected seed: `70003`

Local post-download media inspection:

- H.264 video stream only
- ffprobe dimensions: `1920x1088`
- 24 fps
- duration: `5.041667 s`
- no audio stream present

### Important observer failure

The GitHub matrix job itself ended with a red/failure conclusion **after the generation succeeded** because the optional inspection step called `ffprobe`, but the current hosted `ubuntu-24.04` runner image reported:

```text
ffprobe: command not found
```

The subsequent Artifact upload still succeeded and contained the completed MP4 plus task metadata.

Therefore:

- Seedance generation = success.
- GitHub post-generation media inspector = failure (exit 127 due missing executable).
- It is invalid to infer model failure from the workflow's aggregate red status.

This is a direct example of an observer/instrumentation failure that must not be conflated with failure of the object being measured.

## Result B — doubao-seedance-1-0-lite-t2v-250428

The request did not reach task creation.

- create HTTP status: `404`
- final state: `create_failed`
- returned error code: `InvalidEndpointOrModel.NotFound`
- service message: the model/endpoint does not exist **or** the current account does not have access to it.
- no task ID was returned.
- no output MP4 was produced.

### Narrow causal attribution

The API deliberately collapses at least two possible causes into this error message:

1. exact model/endpoint is unavailable/nonexistent in this runtime context;
2. exact model/endpoint exists but the current account/API key lacks access.

Therefore the experiment establishes only:

> `doubao-seedance-1-0-lite-t2v-250428` is **not executable through the current account + Bearer inference path at this time under this exact ID**.

It does **not** establish:

- which of the two API-reported causes is true;
- that the Seedance Lite family is generally unavailable;
- that another Lite version/endpoint would fail;
- that the account could never regain access later;
- that a management/control-plane listing would report the model absent.

No reverse causal claim is permitted without an additional discriminating source.

## Cross-experiment observations now available

Using the same standardized text prompt/request family:

- 1.0 Pro 250528: executable; observed service default `1080p`; `246840` tokens; no audio stream.
- Fast 251015: executable; observed service default `1080p`; `246840` tokens; no audio stream.
- 1.5 Pro 251215: executable; observed service default `720p`; `108900` tokens; real AAC stereo audio stream when `generate_audio` was omitted.
- Lite T2V 250428: exact current route rejected before task creation with `InvalidEndpointOrModel.NotFound`.

The matching 246840 token values for Pro 250528 and Fast 251015 under the same 5-second/16:9/observed-1080p request are a stronger repeated observation than a single sample, but still should not be promoted into a universal pricing formula without the provider's token-accounting rule or more controlled dimension tests.

## Epistemic status

- Pro 250528 minimal T2V executability: `conditional_deterministic`, evidence `E2E`.
- Lite T2V 250428 exact current route: `F` for this exact account/model/path; cause remains non-identifiable between the alternatives explicitly returned by the provider.
- Pro observed 1080p/no-audio/246840 metadata under this request: `T` observation.
- Pro latency ~70.8 s: one operational sample only; no stable latency ranking.
- GitHub ffprobe absence on this runner image: `T` tooling/environment observation; not a Seedance capability statement.

## Method consequence

Future experiment harnesses must separate:

1. **core task verdict** (create → poll → succeeded/failed),
2. **asset retrieval verdict**,
3. **observer/instrumentation verdict**.

An optional observer failure must not overwrite the core task verdict. Media inspection should either be performed in an environment where the tool is confirmed available or degrade gracefully when the observer is absent.
