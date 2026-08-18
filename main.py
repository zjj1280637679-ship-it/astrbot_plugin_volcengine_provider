"""AstrBot plugin entrypoint.

Importing providers registers both Provider types before AstrBot creates
configured instances. Plugin initialization only migrates old plugin
video settings; it does not author model capability feedback.
"""

from astrbot.api import logger, star

from . import providers as _providers  # noqa: F401
from .adapters.limits import MediaLimits, set_limits
from .adapters.logging import install_video_log_redaction, remove_video_log_redaction
from .capabilities import (
    acquire_dashboard_asset_bridge,
    acquire_dashboard_runtime_bridge,
    acquire_model_fields_bridge,
    configure_cache_log,
    migrate_legacy_video_settings,
    release_dashboard_asset_bridge,
    release_dashboard_runtime_bridge,
    release_model_fields_bridge,
)
from .registry import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    acquire_owned_dashboard_bridge,
    release_owned_dashboard_bridge,
)


def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _media_limits_from_config(config: dict | None) -> MediaLimits:
    """Resolve the runtime media limits from AstrBot plugin configuration."""
    settings = config if isinstance(config, dict) else {}
    return MediaLimits(
        audio_max_bytes=_bounded_int(settings.get("audio_max_mb"), 25, 1, 100) * 1024 * 1024,
        audio_transcode_timeout_seconds=_bounded_int(
            settings.get("audio_transcode_timeout_seconds"), 120, 10, 3600
        ),
        video_max_bytes=_bounded_int(settings.get("video_max_mb"), 200, 1, 4096) * 1024 * 1024,
        video_transcode_timeout_seconds=_bounded_int(
            settings.get("video_transcode_timeout_seconds"), 300, 30, 7200
        ),
        image_compress_enabled=bool(settings.get("image_compress_enabled", True)),
        image_max_bytes=_bounded_int(settings.get("image_max_mb"), 5, 1, 100) * 1024 * 1024,
        image_compress_max_size=_bounded_int(settings.get("image_compress_max_size"), 1280, 256, 8192),
        image_compress_quality=_bounded_int(settings.get("image_compress_quality"), 85, 30, 100),
    )


class VolcengineProviderPlugin(star.Star):
    def __init__(self, context: star.Context, config=None):
        super().__init__(context)
        settings = config if isinstance(config, dict) else {}
        limits = _media_limits_from_config(config)
        set_limits(limits)
        configure_cache_log(
            enabled=settings.get("cache_log_enabled", True),
            every=_bounded_int(settings.get("cache_log_every"), 10, 1, 1000),
        )
        logger.info(
            "Volcengine media limits: audio=%dMiB/%ds video=%dMiB/%ds "
            "image_compress=%s image<=%dMiB (%dpx q%d); cache_log=%s/every=%d",
            limits.audio_max_bytes // (1024 * 1024),
            limits.audio_transcode_timeout_seconds,
            limits.video_max_bytes // (1024 * 1024),
            limits.video_transcode_timeout_seconds,
            limits.image_compress_enabled,
            limits.image_max_bytes // (1024 * 1024),
            limits.image_compress_max_size,
            limits.image_compress_quality,
            settings.get("cache_log_enabled", True),
            _bounded_int(settings.get("cache_log_every"), 10, 1, 1000),
        )
        self._dashboard_bridge_acquired = False
        self._dashboard_asset_bridge_acquired = False
        self._dashboard_runtime_bridge_acquired = False
        self._model_fields_bridge_acquired = False
        self._video_log_filter = install_video_log_redaction()
        try:
            self._dashboard_bridge_acquired = acquire_owned_dashboard_bridge()

            # The lower, Volcengine-owned per-model request rows are a backend
            # model-card capability and must not disappear merely because either
            # Dashboard delivery mechanism is unavailable. Their save boundary
            # scopes persistence to our two Provider Source types independently.
            self._model_fields_bridge_acquired = acquire_model_fields_bridge()

            # This compiled-asset bridge remains the preferred path when one
            # concrete Dashboard bundle exposes all three known structural
            # boundaries. Its successful installation alone is not evidence that
            # the served bundle matched or reached the browser.
            self._dashboard_asset_bridge_acquired = acquire_dashboard_asset_bridge()

            # A real installation may serve a separately built 4.27.x WebUI whose
            # minified identifiers differ from the CI-built chunk. Inject a second
            # bridge through the host index resolver. It waits for one concrete
            # AstrBotConfig model-card component, resolves ownership only through
            # iterable.provider_source_id -> Provider Source type, and mutates that
            # card's ordinary reactive data/private metadata so normal AstrBot
            # rendering, v-model updates and save persistence remain authoritative.
            self._dashboard_runtime_bridge_acquired = acquire_dashboard_runtime_bridge()
        except Exception:
            if self._dashboard_runtime_bridge_acquired:
                release_dashboard_runtime_bridge()
                self._dashboard_runtime_bridge_acquired = False
            if self._dashboard_asset_bridge_acquired:
                release_dashboard_asset_bridge()
                self._dashboard_asset_bridge_acquired = False
            if self._model_fields_bridge_acquired:
                release_model_fields_bridge()
                self._model_fields_bridge_acquired = False
            if self._dashboard_bridge_acquired:
                release_owned_dashboard_bridge()
                self._dashboard_bridge_acquired = False
            remove_video_log_redaction(self._video_log_filter)
            self._video_log_filter = None
            raise
        logger.info(
            "Volcengine providers registered: %s, %s; dashboard_bridge=%s; "
            "model_fields_bridge=%s; dashboard_asset_wrapper=%s; "
            "dashboard_runtime_index_bridge=%s; restart AstrBot after "
            "install/update/disable because the provider type registry has no "
            "safe plugin-owned unload hook",
            ARK_PROVIDER_TYPE,
            AGENT_PLAN_PROVIDER_TYPE,
            "active" if self._dashboard_bridge_acquired else "host-unavailable",
            "active" if self._model_fields_bridge_acquired else "host-unavailable",
            "active" if self._dashboard_asset_bridge_acquired else "host-unavailable",
            "active" if self._dashboard_runtime_bridge_acquired else "host-unavailable",
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
        if getattr(self, "_dashboard_runtime_bridge_acquired", False):
            release_dashboard_runtime_bridge()
            self._dashboard_runtime_bridge_acquired = False
        if getattr(self, "_dashboard_asset_bridge_acquired", False):
            release_dashboard_asset_bridge()
            self._dashboard_asset_bridge_acquired = False
        if getattr(self, "_model_fields_bridge_acquired", False):
            release_model_fields_bridge()
            self._model_fields_bridge_acquired = False
        if getattr(self, "_dashboard_bridge_acquired", False):
            release_owned_dashboard_bridge()
            self._dashboard_bridge_acquired = False
        return None
