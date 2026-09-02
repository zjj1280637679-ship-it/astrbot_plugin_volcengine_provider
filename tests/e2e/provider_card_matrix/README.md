# Current Provider-card E2E contracts

This directory contains only the browser code used by the **current** release gates.

- `current_release_ui_contract.py` — release entrypoint: real AstrBot Dashboard, Ark + Agent Plan Video checkbox, visible click/check, save/reopen, typed request fields, foreign isolation.
- `current_lifecycle_contract.py` — lifecycle entrypoint: real process restart, same-version replacement and uninstall cleanup.
- `model_card_browser_core.py` — shared user-interaction core for the release entrypoint.
- `lifecycle_browser_core.py` — shared lifecycle implementation.
- `foreign_scope_matrix.py` — xAI/Gemini foreign-card isolation.
- `browser_matrix.py`, `assertions.py` — common browser helpers.

A version number in a historical filename is not needed here. Superseded/manual/paid-provider matrices live in Git history, not the current release surface.

The success definition is **observable model-card state and persistence**. No Volcengine paid request is required by these UI contracts.
