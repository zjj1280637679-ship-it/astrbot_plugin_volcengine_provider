# Provider Card Matrix E2E

This directory validates product paths that unit tests cannot prove: provider-card layout, create/edit/save/reload reachability, provider isolation, and later real Volcengine API execution.

Read `docs/E2E_MATRIX.md` before extending this suite.

## Layers

1. `matrix.json` — declarative provider/card/UI path inventory.
2. `runner.py` — validates matrix integrity and emits a deterministic plan.
3. `assertions.py` — structural assertions shared by service-level and browser-level tests.
4. future browser harness — collects DOM/layout snapshots and screenshots from real AstrBot Dashboard.
5. future real-API harness — executes ordinary Ark and Agent Plan paths with repository secrets.

## Design constraints

- A skipped path must include a reason; it is never counted as pass.
- Foreign providers are first-class test cases, not incidental negatives.
- UI correctness includes field ownership, visibility, group/order, create/edit parity, and save/reload behavior.
- Runtime failures are classified by provenance; the suite must not convert every failure into a model-capability verdict.
- Browser screenshots are review evidence, while structural snapshots carry the stable assertions.
- Secrets must never be written into snapshots, logs, or artifacts.

## Local dry run

```bash
python tests/e2e/provider_card_matrix/runner.py
```

The dry run requires no AstrBot process and no API key. It verifies that the declared matrix is internally consistent before expensive E2E stages are added.
