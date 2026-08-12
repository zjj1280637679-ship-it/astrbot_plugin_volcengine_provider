# PROJECT_STATE 0.1.18 — historical snapshot summary

Lifecycle: **COLD / historical**

This file preserves the previous HOT frontier that occupied `docs/PROJECT_STATE.json` before 0.1.19 development became active.

## Published state

- Repository release: `0.1.18`
- Main release commit: `22444f47154f4f88ff3157d6e6ffcce9ad2689f0`
- Stable runtime commit: `4586aa2eb573eb97a72baaaa152c727e3b35530e`
- Main gate: `31589741300` passed
- Publisher: `31589815606` passed release-critical prepare/pre-promotion/promotion/post-promotion stages
- Cleanup repair main commit: `9feb0d5902f4bdc88ea69b08f6d3bee25fcf8f2e`
- Cleanup repair gate: `31590820116` passed
- Cleanup repair no-op publisher: `31590908018` passed

## Completed 0.1.18 goal

Move visible per-model video selection away from the unreliable shared top capability surface and into the exact owned Provider Source, while keeping `volcengine_video_input_enabled` as per-card runtime truth.

The Source presentation switch `volcengine_video_controls_visible` only shows/hides the exact-Source selector. Hidden selections remain active. Foreign Sources receive no field. AstrBot `modalities` remain host-owned.

## Historical validation frontier

The previous HOT frontier was external observation of:

- AstrBot Store refresh visibility for 0.1.18;
- a real Windows Store installation of 0.1.18.

Those observations were still externally unobserved when 0.1.19 development started. They remain historical release observations, but they no longer drive the active 0.1.19 implementation goal.

## Why this was demoted

0.1.19 changes the active project goal from Source-level video UI isolation to **saved-model-card bilingual horizontal request settings**. Keeping the 0.1.18 external-store frontier in the HOT state would cause goal drift: future agents could optimize for a completed release's observation task instead of the current implementation release.

## Exact old snapshot

The exact pre-demotion JSON was blob `282ace47e51b7985abc2564883eb7b07256e93dd` on the 0.1.19 development branch before the lifecycle cleanup. Git history remains the byte-exact archive.

Use `docs/TEST_HISTORY.md`, `CHANGELOG.md`, ADR-0003/0004, and Git history for detailed 0.1.18 evidence.
