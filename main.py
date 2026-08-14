"""AstrBot plugin entrypoint.

Importing providers registers both Provider types before AstrBot creates
configured instances. Plugin initialization only migrates old plugin
video settings; it does not author model capability feedback.
"""

from astrbot.api import logger, star

from . import providers as _providers  # noqa: F401
from .adapters.logging import install_video_log_redaction, remove_video_log_redaction
from .capabilities import (
    acquire_dashboard_asset_bridge,
    acquire_model_fields_bridge,
    migrate_legacy_video_settings,
    release_dashboard_asset_bridge,
    release_model_fields_bridge,
)
from .capabilities.video_modality_fallback import (
    acquire_video_modality_fallback_bridge,
    release_video_modality_fallback_bridge,
)
from .registry import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    acquire_owned_dashboard_bridge,
    release_owned_dashboard_bridge,
)


class VolcengineProviderPlugin(star.Star):
    def __init__(self, context: star.Context):
        super().__init__(context)
        self._dashboard_bridge_acquired = False
        self._video_modality_fallback_acquired = False
        self._dashboard_asset_bridge_acquired = False
        self._model_fields_bridge_acquired = False
        self._video_log_filter = install_video_log_redaction()
        try:
            self._dashboard_bridge_acquired = acquire_owned_dashboard_bridge()
            self._video_modality_fallback_acquired = (
                acquire_video_modality_fallback_bridge()
            )
            self._dashboard_asset_bridge_acquired = acquire_dashboard_asset_bridge()
            if self._dashboard_asset_bridge_acquired:
                self._model_fields_bridge_acquired = acquire_model_fields_bridge()
        except Exception:
            if self._model_fields_bridge_acquired:
                release_model_fields_bridge()
                self._model_fields_bridge_acquired = False
            if self._dashboard_asset_bridge_acquired:
                release_dashboard_asset_bridge()
                self._dashboard_asset_bridge_acquired = False
            if self._video_modality_fallback_acquired:
                release_video_modality_fallback_bridge()
                self._video_modality_fallback_acquired = False
            if self._dashboard_bridge_acquired:
                release_owned_dashboard_bridge()
                self._dashboard_bridge_acquired = False
            remove_video_log_redaction(self._video_log_filter)
            self._video_log_filter = None
            raise
        logger.info(
            "Volcengine providers registered: %s, %s; dashboard_bridge=%s; "
            "video_modality_fallback=%s; model_fields_bridge=%s; "
            "dashboard_asset_bridge=%s; restart AstrBot after install/update/disable "
            "because the provider type registry has no safe plugin-owned unload hook",
            ARK_PROVIDER_TYPE,
            AGENT_PLAN_PROVIDER_TYPE,
            "active" if self._dashboard_bridge_acquired else "host-unavailable",
            "active"
            if self._video_modality_fallback_acquired
            else "host-unavailable",
            "active" if self._model_fields_bridge_acquired else "host-unavailable",
            "active" if self._dashboard_asset_bridge_acquired else "host-unavailable",
        )

    async def initialize(self) -> None:
        config = self.context.astrbot_config_mgr.default_conf
        changed_ids = migrate_legacy_video_settings(config)
        if not changed_ids:
            return

        config.save_config()
        changed_set = {provider_id for provider_id in changed_ids if provider_id}
        manager = self.context.provider_manager
        for provider in list(config.get("provider", [])):
            provider_id = str(provider.get("id") or "")
            if provider_id in changed_set and provider_id in manager.inst_map:
                await manager.reload(provider)

        logger.info(
            "Volcengine video transport migration complete: model_cards=%d; "
            "AstrBot capability feedback untouched.",
            len(changed_set),
        )

    async def terminate(self) -> None:
        remove_video_log_redaction(self._video_log_filter)
        self._video_log_filter = None
        if getattr(self, "_model_fields_bridge_acquired", False):
            release_model_fields_bridge()
            self._model_fields_bridge_acquired = False
        if getattr(self, "_dashboard_asset_bridge_acquired", False):
            release_dashboard_asset_bridge()
            self._dashboard_asset_bridge_acquired = False
        if getattr(self, "_video_modality_fallback_acquired", False):
            release_video_modality_fallback_bridge()
            self._video_modality_fallback_acquired = False
        if getattr(self, "_dashboard_bridge_acquired", False):
            release_owned_dashboard_bridge()
            self._dashboard_bridge_acquired = False
        return None
