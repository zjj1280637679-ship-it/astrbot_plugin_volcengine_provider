# Existing Behavior Samples and Seed-Control Gap

## 1. No-cost behavior review of D-002/D-003 outputs

The three successful standardized T2V probes used the same natural-language action request:

> an adult athletic man shadowboxes in a professional gym, performs one controlled jab-cross combination, then resets his guard

Frame samples were extracted from the already-generated videos; no new inference quota was consumed.

### Fast 251015 sample

Visible sampled sequence includes guard states, extended punches and a later return toward guard. A two-punch/action sequence is reachable in this sample.

### 1.5 Pro 251215 sample

Visible sampled sequence clearly alternates guard / punch / punch-or-transition / return-to-guard states. Ordered-action execution is reachable in this sample.

### 1.0 Pro 250528 sample

Visible sampled sequence likewise includes extended punches followed by a guarded ending state. Ordered-action execution is reachable in this sample.

## 2. What these samples establish

They establish **reachability**, not reliability:

- the ordered-action language used in the standard prompt is compatible with successful visible multi-stage motion on all three currently executable exact T2V models;
- the project therefore does not need another generation merely to prove that ordered action language can ever work.

They do not establish:

- adherence probability;
- precise jab-versus-cross correctness;
- timing accuracy;
- stable model ranking;
- causality of the specific wording versus general model behavior.

A one-sample-per-model frame review is not a Q-level benchmark.

## 3. Seed values in the standardized runs

The service returned different seeds for the model probes, for example:

- Fast 251015: `68970`
- 1.5 Pro 251215: `39712`
- 1.0 Pro 250528: `70003`

Therefore visual differences between these samples are confounded by both model identity and service-selected randomness.

## 4. Can Ark Seedance seed currently be controlled? Evidence conflict

### Core official API documentation

The current `CreateContentsGenerationsTasks` parameter list exposes model, content, callback URL and return-last-frame in the parsed core documentation; a request-side `seed` parameter is not present in that parsed parameter list.

The current `GetContentsGenerationsTask` response documentation does expose:

```text
seed — the integer seed used for this request
```

This proves the service has/returns a seed, but does not prove the caller can set it.

### Volcano Engine developer-community Skill article

The article's CLI parameter table advertises:

```text
--seed, -s | random seed (reproducible result)
```

However, the **actual Ark implementation code shown later in the same article** defines:

```python
create_ark_video_task(api_key, prompt, model,
                      first_frame_url=None,
                      last_frame_url=None,
                      resolution=None,
                      duration=None,
                      generate_audio=None)
```

and constructs the Ark request body from:

- `model`
- `content`
- optional `duration`
- optional `generate_audio`

The displayed Ark function does **not** accept or transmit `seed`.

Therefore the article is internally inconsistent for Ark seed control: a CLI-level option exists in the parameter documentation, but the displayed Ark request path does not wire it into the API request.

## 5. Epistemic conclusion

Current status of caller-controlled seed on this exact Ark video task path:

```text
UNKNOWN / NOT ESTABLISHED
```

Do not use `seed` as a hard prompt-experiment control merely because a community Skill exposes a CLI flag.

## 6. Method consequence for prompt-handle experiments

A strict one-seed A/B ablation (same random seed, only prompt handle changed) is not currently available as a justified design assumption.

If prompt-handle reliability becomes load-bearing, choose one of two valid paths:

1. first run a dedicated request-side seed-control experiment that verifies both acceptance **and reproducibility**, if the expected information gain justifies its quota; or
2. use repeated randomized samples with enough observations to estimate a distributional effect instead of pretending randomness was controlled.

Until then, existing successes should be used as reachability evidence only.
