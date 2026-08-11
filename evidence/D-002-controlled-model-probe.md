# D-002 Controlled Model Probe — Result and Causal Attribution

## Question

Does the exact user-listed model ID `doubao-seedance-1-0-pro-fast-251015` execute the same minimal T2V request as the already verified `doubao-seedance-1-5-pro-251215`, and what model-dependent defaults are directly observable when **model_id is the only intentionally changed request variable**?

## Request held constant

Both matrix jobs used the same API endpoint, account secret, prompt and request structure. The payload contained only:

```json
{
  "model": "<matrix model id>",
  "content": [
    {
      "type": "text",
      "text": "Cinematic photorealistic close-up sports training. An adult athletic man shadowboxes in a professional gym, performs one controlled jab-cross combination, then resets his guard. Natural body mechanics, subtle sweat under overhead lights, stable readable motion, no blood, no injury. --ratio 16:9 --dur 5"
    }
  ]
}
```

No top-level `duration`, `resolution`, `generate_audio`, `draft`, or seed was supplied.

Important limitation: the service itself selected different random seeds. Therefore visual quality/content differences are **not** causally attributable only to model architecture from this one sample. Hard metadata/default differences remain directly observable.

## Result A — doubao-seedance-1-0-pro-fast-251015

- create HTTP status: `200`
- task id: `cgt-20260812054334-fnx6g`
- final state: `succeeded`
- poll count: `4`
- wall time observed by the workflow: `39.76443076133728 s`
- reported usage: `246840` completion/total tokens
- reported resolution: `1080p`
- reported ratio: `16:9`
- reported duration: `5`
- reported fps: `24`
- reported draft: `false`
- output format: `mp4`
- downloaded MP4 bytes: `8536017`
- service-selected seed: `68970`

Local deterministic media inspection of the returned MP4:

- H.264 video stream only
- 24 fps
- ffprobe dimensions: `1920x1088`
- duration: `5.041667 s`
- **no audio stream present**

The API's semantic resolution field says `1080p`; ffprobe reports the encoded frame dimensions as 1920x1088. Preserve both observations rather than silently normalizing one into the other.

## Result B — doubao-seedance-1-5-pro-251215

- create HTTP status: `200`
- task id: `cgt-20260812054342-bksbv`
- final state: `succeeded`
- poll count: `6`
- wall time observed by the workflow: `60.13133716583252 s`
- reported usage: `108900` completion/total tokens
- reported resolution: `720p`
- reported ratio: `16:9`
- reported duration: `5`
- reported fps: `24`
- reported `generate_audio`: `true`
- reported draft: `false`
- output format: `mp4`
- downloaded MP4 bytes: `5722251`
- service-selected seed: `39712`

Local deterministic media inspection of the returned MP4:

- H.264 video stream: `1280x720`, 24 fps
- AAC audio stream: 44.1 kHz, stereo
- duration: `5.050000 s`

Therefore `generate_audio:true` in the returned metadata corresponds to a **real encoded audio stream**, not merely a metadata flag.

## Narrow conclusions supported by this experiment

### Causal / execution conclusions

1. The exact model ID `doubao-seedance-1-0-pro-fast-251015` is executable in the current account for this minimal 5-second 16:9 T2V request shape.
2. With the same intentionally controlled request fields, the two exact model IDs produced different service-selected defaults/metadata:
   - Fast 251015: reported 1080p, 246840 tokens, no audio stream.
   - 1.5 Pro 251215: reported 720p, 108900 tokens, `generate_audio:true`, real AAC stereo audio stream.
3. Because neither request supplied `generate_audio`, the observed positive audio behavior of 1.5 Pro is a **model/request-shape default under this tested condition**. It is not caused by an explicit enable-audio parameter in this experiment.
4. Because neither request supplied a resolution parameter, the observed 720p vs 1080p results are service/model defaults under this tested condition, not explicit user-selected resolution controls.
5. Prompt-suffix `--ratio 16:9 --dur 5` produced matching reported ratio/duration in both runs. This is consistent with the official API examples, but this experiment was not designed to compare prompt-suffix controls against alternative top-level controls.

### One-sample observations that must NOT be promoted to stable performance claims

- Fast completed in ~39.8 s while 1.5 Pro completed in ~60.1 s.
- Fast used more tokens in this request because its observed default output was 1080p while 1.5 Pro's observed default was 720p and included audio.
- Artifact/file sizes differed.

These are real observations but are not yet stable latency, cost-efficiency, or quality distributions. Service load, random seed, encoding behavior and other uncontrolled runtime factors remain possible contributors.

## What failure/success does not establish

This experiment does not establish:

- Fast 251015 image-to-video capability;
- Fast 251015 first/last-frame support;
- native audio enable/disable parameter semantics for either model;
- stable speed superiority;
- visual quality superiority;
- prompt-handle reliability;
- universal token-cost formula;
- exact behavior at other durations/resolutions/ratios.

## Epistemic classification

- Fast 251015 minimal T2V executability: `conditional_deterministic`, evidence `E2E`.
- 1.5 Pro omitted-audio-parameter → audio-present under this exact request shape: `conditional_deterministic observation`, evidence `T/E2E` for this domain.
- Default-resolution differences under this exact request shape: `conditional_deterministic observation`, evidence `T`.
- Latency ranking: `probabilistic/operational`, one sample only; no `Q` claim.
- Visual-quality ranking: `probabilistic`, unmeasured in this experiment.

## Decision consequence

The exact Fast 251015 model can now enter the executable model graph for **minimal T2V**, but it must not inherit untested I2V/audio/first-last-frame capabilities from other Fast suffixes.

A further generation experiment should be run only when a load-bearing decision requires one of those unknown capabilities or a statistically meaningful quality/speed comparison. No further generation is justified merely to reconfirm this T2V result.
