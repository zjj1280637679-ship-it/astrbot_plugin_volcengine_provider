# AI Modification Rules

## Purpose

This document is an entry point for AI coding agents and maintainers. It defines what may be inferred from project evidence and what must not be invented.

## Core rules

1. Runtime feedback is evidence, not permanent truth.

A model card, `/models` response, UI badge, or metadata field describes an observed state. It does not authorize the plugin to permanently decide model capability.

2. Provider scope must be preserved.

The plugin adapts Volcengine Ark protocol differences. It must not replace AstrBot responsibilities such as:

- conversation lifecycle
- fallback policy
- retry policy
- key rotation
- QQ media lifecycle
- global model capability authority

3. Prefer evidence over assumptions.

When changing behavior, identify:

- observation
- evidence source
- inference
- decision

Do not convert an unverified assumption into runtime behavior.

4. Preserve future compatibility.

Unknown fields and future modality tokens should be preserved when they are information, not discarded because the current adapter does not understand them.

5. Test boundaries matter.

Raw provider API tests do not prove QQ compatibility. QQ compatibility requires the full chain:

QQ -> NapCat -> AstrBot -> MediaResolver -> Adapter -> Provider.

## Safe extension pattern

New capabilities should normally add:

- new evidence source
- new adapter translation
- new tests

They should not add a parallel lifecycle or duplicate AstrBot ownership.
