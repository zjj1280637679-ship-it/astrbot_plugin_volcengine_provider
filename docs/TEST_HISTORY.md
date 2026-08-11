# Test History

This file records important validation evidence and prevents future agents from confusing missing reruns with missing capability.

| Version | Area | Evidence | Meaning |
|---|---|---|---|
| 0.1.12 | QQ audio | Full QQ media chain validated | QQ audio path worked under original conditions |
| 0.1.12 | QQ video | Full video attachment chain validated | Video path worked under original conditions |
| 0.1.13 | Architecture | Boundary regression passed | Provider does not own AstrBot lifecycle |
| 0.1.14 | Compatibility | AstrBot 4.26.1 / 4.27.2 matrix passed | Host integration remained compatible |
| 0.1.15 | Capability boundary | Runtime feedback isolation validated | Feedback is not capability authority |
| 0.1.16 | Runtime evidence | Raw vs plugin attribution matrix passed | Failures can be separated by layer |

## Revalidation rules

A historical success remains valid when:

- related code is unchanged;
- dependencies are unchanged;
- ownership boundaries are unchanged.

A full rerun is required when:

- media adapters change;
- AstrBot media interfaces change;
- provider payload format changes;
- QQ integration layer changes.

## Important distinction

A raw API fixture is not equivalent to a QQ user event.

QQ compatibility requires testing the complete user path:

QQ -> NapCat -> AstrBot -> MediaResolver -> Provider adapter -> model.
