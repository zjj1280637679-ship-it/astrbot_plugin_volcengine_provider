# Legacy feature baseline for 0.1.23+

This file is a regression inventory, not a request to restore every historical UI literally.

The current plugin is cumulative. A Video UI repair must preserve the useful behavior accumulated before 0.1.22 unless an explicit replacement is tested.

## Runtime/provider capabilities that must remain

- Ordinary Ark and Agent Plan remain separate provider source types with fixed, non-crossing billing endpoints and the local `agentplan/` namespace.
- Text/image/audio/tool behavior continues through AstrBot's native OpenAI-compatible provider lifecycle rather than a second routing/retry stack.
- Current trusted video attachments can be serialized to Ark `video_url`; disabled Video must not perform that conversion.
- Original video mode preserves the existing resolver path; Compressed mode uses ffmpeg/H.264 MP4 and fails closed instead of silently falling back to original quality.
- QQ/Tencent audio continues through AstrBot media resolution and the Ark final WAV invariant before `input_audio` serialization.
- Provider-owned SDK log redaction for video URLs and audio base64 remains reversible.

## Per-model settings that must remain

The Ark / Agent Plan model-card editing surface must retain these settings and their persistence/request semantics:

- Video capability: the native `modalities` Video checkbox is the enable/disable UI truth when available.
- Video Quality: Compressed / Original Quality.
- Thinking Mode: Default / Disabled / Enabled / Auto.
- Reasoning Effort: Default / Low / Medium / High.
- Temperature.
- Top P.
- Max Output Tokens.
- Stop Sequences.
- Frequency Penalty.
- Presence Penalty.
- AstrBot `custom_extra_body` remains the escape hatch for model-specific or not-yet-promoted request fields.

Explicit horizontal fields outrank the same key in `custom_extra_body`; empty optional values mean "do not inject". Numeric validation must continue to reject non-finite values where applicable.

## Migration and persistence behavior that must remain

- Historical per-card and Source-era video state may be read only through the existing migration precedence; wrong-Source/foreign debris must not become owned runtime truth.
- Disabling Video keeps the saved compressed/original quality preference.
- Save/reopen must preserve the current card's Video selection and advanced settings.
- Plugin UI/service wrappers and temporary Dashboard assets remain reversible on release/unload.

## Historical UI that is not itself a required product surface

The 0.1.18 Provider Source master switch and Source model selector are historical implementations. Their useful semantics (exact Source ownership, migration, rollback discipline, preserving per-card intent) remain valuable, but their visual controls are not required to return if the model-card Video capability is available reliably.

## Change rule

A future implementation may redesign the mechanism and may accept bounded UI side effects, but it must not delete the capabilities above merely to make the Video checkbox appear. Any intentional removal requires a dedicated regression decision and replacement evidence.
