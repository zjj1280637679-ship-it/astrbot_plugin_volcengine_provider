# ADR-0004: Migration preserves user intent, not model capability truth

## Status

Accepted/current compatibility rule.

## Context

Older plugin versions stored video choices in several temporary or legacy fields. Those values are historical user configuration, not authoritative facts about a model's capability.

## Decision

Startup migration may use legacy Volcengine fields only to recover an owned card's prior user intent into the current compatibility/runtime mirror.

The current implementation preserves this precedence when the current mirror is missing:

1. exact-Source retired model-dialog boolean;
2. older per-card Volcengine boolean;
3. older explicit owned-Source boolean, including explicit `false`;
4. historical `video` membership in `modalities` as a final migration clue.

Presence and type are checked explicitly so `false` remains information. Wrong-Source, foreign and wrong-layer plugin fields are debris and are removed rather than promoted.

Migration itself does not rewrite the native `modalities` list. Normal current model-card save is a different boundary: for an owned card it mirrors current native `modalities` membership into `volcengine_video_input_enabled` so request-time transport follows the user's current checkbox.

Source-level presentation fields and temporary selector keys are retired debris and must not persist on current Sources or cards.

## Consequences

- upgrades preserve an owned user's prior Video choice where it can be attributed safely;
- foreign cards cannot acquire Volcengine state from legacy debris;
- migration never turns historical configuration into a permanent model-capability claim;
- the current visible truth remains the owned model card's native Video checkbox after the user saves the card.
