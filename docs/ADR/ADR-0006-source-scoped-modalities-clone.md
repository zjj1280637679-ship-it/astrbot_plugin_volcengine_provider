# ADR-0006: Source-scoped modalities adaptation occurs on the dialog clone

## Status

Accepted for 0.1.20. The structural contract passed locally against the
bundled AstrBot 4.27.2 Dashboard asset. A real approved Windows AstrBot
instance showed the Ark video checkbox, preserved it after save/reopen, kept a
foreign provider unchanged, and left the original Dashboard asset untouched.
Agent Plan and marketplace-installed runtime observation remain release-frontier
evidence rather than premises of this decision.

## Context

ADR-0003 correctly rejected changing the shared backend `modalities` schema:
that object has no current Provider Source identity, so adding `video` there
made the checkbox appear for every provider or none. The missing distinction
was between that shared schema instance and the private schema clone created by
AstrBot's provider-model dialog.

AstrBot 4.27.2's `useProviderModelConfigDialog` clone boundary simultaneously
has both facts required by the decision:

- a deep clone of the model-card schema;
- the selected Provider Source `type`.

That is a new concrete isolation boundary, not a reason to mutate the shared
schema or infer a model capability.

## Decision

The plugin may adapt the existing `modalities` checklist only after AstrBot has
created the current dialog's private schema clone:

```text
selected Source type in {Ark, Agent Plan}
  -> append video to this clone's modalities options
  -> show this plugin's request-setting rows

selected Source type outside that set
  -> leave modalities unchanged
  -> mark this plugin's request-setting rows invisible
```

The checkbox writes the ordinary model-card `modalities` list. At the owned
model-card save boundary, the plugin mirrors membership of `video` into the
legacy/runtime `volcengine_video_input_enabled` Boolean. In this context the
entry is explicit user transport intent; it is not provider feedback or a
permanent claim that the selected model supports video.

AstrBot currently exposes no official plugin hook for that frontend clone. The
plugin therefore wraps the static-file resolver reversibly and serves one
temporary transformed copy of the uniquely matched provider-dialog asset. It
does not modify AstrBot files on disk. On termination it restores the prior
resolver and removes the temporary copy.

Compatibility is an optional UI capability, not a plugin load gate. Startup
first requires exactly one structural match. Zero or multiple matches leave
the original Dashboard untouched and skip the model-field backend bridge while
the Volcengine providers continue to load.

## Required invariants

- Ark and Agent Plan model dialogs show `video` inside the existing
  `modalities` checklist.
- Foreign provider dialogs retain their original `modalities` options and show
  none of the Volcengine-only rows.
- A checked/unchecked video option persists as present/absent in `modalities`
  and as a matching compatibility Boolean on owned cards.
- Foreign save payloads cannot create Volcengine state.
- Unknown future modality tokens are preserved.
- A changed/ambiguous Dashboard asset is returned byte-for-byte unchanged and
  does not prevent provider registration.
- Plugin termination restores the exact previous static-file resolver and
  removes only the plugin-owned temporary artifact.

## Relationship to ADR-0003

ADR-0003 remains correct for direct mutation of the shared schema and for host
versions where no verified per-dialog identity boundary exists. This ADR
supersedes only its conclusion that every presentation of a fifth checkbox in
the existing modalities row is impossible: the clone-plus-Source boundary now
supplies the missing object identity.

## Reconsideration

Replace the asset bridge when AstrBot provides an official provider-scoped
model-schema or Dashboard-extension hook. Re-run the structural probe and real
Dashboard matrix whenever the bundled provider panel changes.
