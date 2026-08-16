"""Narrow compatibility shims for current AstrBot behavior.

Remove a shim when the corresponding host behavior disappears; do not put
Volcengine protocol logic in this module.
"""

from __future__ import annotations

ASTRBOT_KEY_PREFIX_LOG_COMPAT = "ProviderOpenAIOfficial logs chosen_key[:12] on 429"


class _ApiKeyLogView(str):
    """Preserve a real API key while redacting the slice AstrBot logs on 429.

    This object is passed only into AstrBot's native error-recovery method.
    Equality and hashing stay identical to ``str``, so the framework still owns
    key-pool membership, removal, selection and retry policy.  Only indexing is
    redacted because AstrBot currently logs ``chosen_key[:12]`` on rate limits.
    """

    def __getitem__(self, key):
        if isinstance(key, slice):
            return "[REDACTED_API_KEY]"
        return "*"

