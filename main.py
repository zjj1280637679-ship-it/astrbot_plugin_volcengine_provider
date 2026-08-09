"""AstrBot plugin entrypoint.

Importing ``providers`` registers both provider cards before AstrBot creates
configured provider instances during cold startup.
"""

from astrbot.api import logger, star

from .providers import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    install_video_log_redaction,
    remove_video_log_redaction,
)
from .registry import acquire_owned_provider_schema, release_owned_provider_schema


class VolcengineProviderPlugin(star.Star):
    def __init__(self, context: star.Context):
        super().__init__(context)
        self._provider_schema_acquired = False
        self._video_log_filter = install_video_log_redaction()
        try:
            acquire_owned_provider_schema()
            self._provider_schema_acquired = True
        except Exception:
            remove_video_log_redaction(self._video_log_filter)
            self._video_log_filter = None
            raise
        logger.info(
            "Volcengine providers registered: %s, %s; restart AstrBot after "
            "install/update/disable because AstrBot 4.26 has no provider "
            "registry unload hook",
            ARK_PROVIDER_TYPE,
            AGENT_PLAN_PROVIDER_TYPE,
        )

    async def terminate(self) -> None:
        remove_video_log_redaction(self._video_log_filter)
        self._video_log_filter = None
        if getattr(self, "_provider_schema_acquired", False):
            release_owned_provider_schema()
            self._provider_schema_acquired = False
        # Provider instances own and close their HTTP clients through AstrBot's
        # ProviderManager.  The process-global type registry has no safe unload
        # hook in 4.26.x, so removal takes effect after a full restart.
        return None
