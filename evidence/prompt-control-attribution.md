# Prompt and Generation-Control Attribution — v0.1

Purpose: separate what the Seedance API is documented to control, what our successful runs merely accepted, and what still requires causal isolation.

## 1. Official hard evidence available now

The Ark `CreateContentsGenerationsTasks` documentation explicitly shows generation controls embedded in the text prompt, including examples such as:

- `--ratio 16:9`
- `--ratio adaptive`
- `--dur 5`

The same API documents:

- `content[]` text and image inputs;
- asynchronous task creation;
- optional `callback_url`;
- optional `return_last_frame` for retrieving a PNG final frame after generation.

Therefore the prompt compiler may currently treat prompt-suffix ratio/duration controls and `return_last_frame` as documented API-surface controls.

## 2. Confounded controls in our previous E2E runs

The successful 1.5 Pro image-to-video workflow sent both:

```text
... --ratio 16:9 --dur 5
```

and JSON fields:

```json
{
  "duration": 5,
  "generate_audio": false
}
```

The returned task metadata reported:

- `duration: 5`
- `ratio: 16:9`
- `resolution: 720p`
- `framespersecond: 24`
- `generate_audio: false`
- `draft: false`
- `output_format: mp4`
- `usage.total_tokens: 108900`

The earlier 5-second text-to-video run also reported `usage.total_tokens: 108900` with the same 720p / 16:9 / 24 fps / no-audio output profile.

### What this proves

- The complete request shape was accepted by `doubao-seedance-1-5-pro-251215`.
- The final output was 5 seconds, 16:9, 720p, 24 fps, no audio.
- Two distinct 5-second/no-audio 720p runs (T2V and I2V) both reported 108900 completion/total tokens.

### What this does NOT prove

- It does not isolate whether top-level `duration` caused the 5-second duration, because `--dur 5` was present simultaneously.
- It does not isolate whether a top-level ratio field would work; we did not send one.
- It does not prove `generate_audio: false` changed behavior rather than matching a default.
- It does not prove the token usage is universally fixed at 108900 for every 5-second 720p no-audio request; two matching observations make this a strong candidate relation, not yet a universal rule.

## 3. Image-role attribution

Our successful I2V request supplied one `image_url` with no explicit role:

```json
{
  "type": "image_url",
  "image_url": {"url": "..."}
}
```

This proves a single image can participate successfully in I2V for the exact tested model.

It does not by itself prove the generic semantics of an unlabelled image for every model/version (first frame vs reference image vs another provider-defined interpretation).

Volcano Engine developer-community implementation material shows role-based patterns such as:

- `role: "first_frame"`
- `role: "last_frame"`

and reports first+last-frame support for some Seedance models. Because these are implementation/community sources rather than the currently parsed core API parameter table, treat them as candidate schema until either a stronger official source is retrieved or the exact mode is tested when needed.

## 4. Native audio attribution

Volcano Engine product/developer materials describe Seedance 1.5 Pro as supporting audio generation / audio-video synchronized output.

Current project evidence:

- `generate_audio: false` was accepted and the returned result reported `generate_audio: false`.
- No positive audio-generation run has been performed.

Therefore:

- product capability: documented/candidate;
- exact request control for enabling audio: not yet promoted to E2E;
- audio prompt-handle behavior: probabilistic and entirely unbenchmarked.

Do not spend quota to test audio until a user task actually requires native audio or until audio support becomes load-bearing for routing.

## 5. Prompt-guide evidence

Volcano Engine currently publishes dedicated official prompt-guide pages for:

- Seedance 1.5 Pro;
- Seedance 1.0 series.

The current retrieval environment can confirm these official documents exist and their update dates, but the JavaScript-rendered page body is not available through the current parser. Therefore their mere existence cannot be used to invent detailed prompt rules.

Developer-community implementation material suggests candidate natural-language handles including:

- explicit camera movement;
- ordered action sequences (`first / then / next`);
- multi-shot narration with shot labels;
- concrete verbs and details rather than vague descriptions.

These are hypotheses/engineering leads, not quality guarantees.

## 6. Current prompt compiler policy

Until further evidence exists:

### Hard controls

- Model ID: explicit exact ID.
- Ratio/duration: use the documented prompt-suffix form (`--ratio`, `--dur`) for production requests.
- Image input: use the already E2E single-image `image_url` form for the exact 1.5 Pro mode tested.
- `return_last_frame`: may be used as a documented task-level option when continuity is actually required.

### Unconfirmed controls

Do not rely on these as causally proven without a load-bearing reason to test:

- top-level `duration` as the sole duration control;
- positive `generate_audio: true` behavior;
- `draft` control;
- explicit first/last-frame role semantics for each exact model ID;
- seed reproducibility;
- resolution control outside the observed default/result path.

### Natural-language handles

Treat identity locking, POV, camera motion, ordered action sequences, temporal segments, negative constraints, and multi-shot labels as probabilistic model-behavior hypotheses. They require controlled repeated comparison if they become routing/quality claims.

## 7. Next experiment selection rule

A prompt/control experiment is justified only if:

1. two plausible controls cannot be distinguished from existing evidence;
2. the distinction changes an actual production decision;
3. documentation cannot settle it;
4. the test can isolate one independent variable;
5. the quota/effect is justified by a Rights-Capability-Intent-Effect audit.

This specifically prevents repeating the earlier mistake of adding multiple redundant controls and then attributing success to all of them.
