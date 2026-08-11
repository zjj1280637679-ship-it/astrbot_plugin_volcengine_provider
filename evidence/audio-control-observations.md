# Seedance 1.5 Pro Audio-Control Observations

## Observed runs

Three already-generated `doubao-seedance-1-5-pro-251215` outputs provide audio-control evidence without spending additional quota.

### Run A — earlier text-to-video

Request explicitly supplied:

```json
"generate_audio": false
```

Returned task metadata reported `generate_audio:false`.

Deterministic local media inspection of the downloaded MP4 found only one H.264 video stream and **no audio stream**.

### Run B — earlier single-image image-to-video

Request explicitly supplied:

```json
"generate_audio": false
```

Returned task metadata reported `generate_audio:false`.

Deterministic local media inspection of the downloaded MP4 found only one H.264 video stream and **no audio stream**.

### Run C — D-002 controlled 1.5 Pro T2V baseline

The request **omitted `generate_audio` entirely**.

Returned task metadata reported:

```json
"generate_audio": true
```

Deterministic local media inspection found:

- H.264 video stream;
- AAC audio stream;
- 44.1 kHz;
- stereo.

## Narrow attribution

These three observations support the following operational distinction in the tested 1.5 Pro domain:

- explicit `generate_audio:false` has twice coincided with metadata `false` and video-only MP4 output;
- omitted `generate_audio` has once coincided with metadata `true` and a real AAC audio stream.

This is strong convergent evidence that the field is operationally meaningful and that omission must **not** be assumed equivalent to `false` for `doubao-seedance-1-5-pro-251215`.

It is still not a strict single-variable experiment because the three prompts/modes were not identical. Therefore the project should avoid claiming a complete universal parameter law (for example, all possible requests always default to audio-on). Instead use the narrower production rule below.

## Production rule admitted by current evidence

When silent output is intended on the tested 1.5 Pro API path, explicitly send:

```json
"generate_audio": false
```

Do not rely on omission to produce silence.

When native audio is desired, omission has demonstrated that audio can be produced, but explicit `generate_audio:true` semantics and audio-prompt adherence remain separate unknowns. They should only be tested when an actual task requires them.

## Epistemic classification

- explicit false → silent output in two observed 1.5 Pro runs: `T/E2E observation` within tested domain;
- omission → audio-present in D-002: `E2E observation` within exact D-002 request shape;
- universal default-audio law: **not established**;
- audio semantic/prompt quality: probabilistic and unmeasured.
