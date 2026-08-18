"""AstrBot plugin entrypoint.

Importing providers registers both Provider types before AstrBot creates
configured instances.  Runtime policy (media limits/cache logging) is owned by
plugin configuration; after every plugin initialization the currently loaded
Volcengine Provider instances are rebound so a Dashboard config hot-reload
cannot leave old module globals serving new settings.
"""

from astrbot.api import logger, star

from . import providers as _providers  # noqa: F401
from .adapters.limits import MediaLimits, set_limits
from .adapters.logging import install_video_log_redaction, remove_video_log_redaction
from .capabilities import (
    acquire_dashboard_asset_bridge,
    acquire_dashboard_runtime_bridge,
    acquire_model_fields_bridge,
    cache_log_settings,
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

_OWNED_PROVIDER_TYPES = frozenset({ARK_PROVIDER_TYPE, AGENT_PLAN_PROVIDER_TYPE})


def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _media_limits_from_config(config: dict | None) -> MediaLimits:
    """Resolve runtime media limits from AstrBot plugin configuration."""
    settings = config if isinstance(config, dict) else {}
    return MediaLimits(
        audio_max_bytes=_bounded_int(settings.get("audio_max_mb"), 25, 1, 100)
        * 1024
        * 1024,
        audio_transcode_timeout_seconds=_bounded_int(
            settings.get("audio_transcode_timeout_seconds"), 120, 10, 3600
        ),
        video_max_bytes=_bounded_int(settings.get("video_max_mb"), 200, 1, 4096)
        * 1024
        * 1024,
        video_transcode_timeout_seconds=_bounded_int(
            settings.get("video_transcode_timeout_seconds"), 300, 30, 7200
        ),
        image_compress_enabled=bool(settings.get("image_compress_enabled", True)),
        image_max_bytes=_bounded_int(settings.get("image_max_mb"), 5, 1, 100)
        * 1024
        * 1024,
        image_compress_max_size=_bounded_int(
            settings.get("image_compress_max_size"), 1280, 256, 8192
        ),
        image_compress_quality=_bounded_int(
            settings.get("image_compress_quality"), 85, 30, 100
        ),
    )


async def _reload_owned_provider_instances(context: star.Context) -> list[str]:
    """Rebuild live owned Provider objects after a plugin-policy transition.

    AstrBot reloads plugin configuration by unloading/reimporting the plugin, but
    Provider instances have their own lifecycle.  Without this explicit rebind,
    an already-created Provider can keep calling functions from the old purged
    module and therefore keep the previous media/cache policy.
    """
    config = context.astrbot_config_mgr.default_conf
    manager = context.provider_manager
    inst_map = getattr(manager, "inst_map", {})
    if not isinstance(inst_map, dict):
        inst_map = {}

    reloaded: list[str] = []
    for provider in list(config.get("provider", [])):
        if not isinstance(provider, dict):
            continue
        if str(provider.get("type") or "") not in _OWNED_PROVIDER_TYPES:
            continue
        provider_id = str(provider.get("id") or "").strip()
        if not provider_id or provider_id not in inst_map:
            continue
        await manager.reload(provider)
        reloaded.append(provider_id)
    return reloaded


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
        cache_enabled, cache_every = cache_log_settings()
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
            cache_enabled,
            cache_every,
        )
        self._dashboard_bridge_acquired = False
        self._dashboard_asset_bridge_acquired = False
        self._dashboard_runtime_bridge_acquired = False
        self._model_fields_bridge_acquired = False
        self._video_log_filter = install_video_log_redaction()
        try:
            self._dashboard_bridge_acquired = acquire_owned_dashboard_bridge()
            self._model_fields_bridge_acquired = acquire_model_fields_bridge()
            self._dashboard_asset_bridge_acquired = acquire_dashboard_asset_bridge()
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
            "dashboard_runtime_index_bridge=%s",
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
        if changed_ids:
            config.save_config()

        reloaded_ids = await _reload_owned_provider_instances(self.context)
        from .adapters.limits import get_limits

        active_limits = get_limits()
        cache_enabled, cache_every = cache_log_settings()
        logger.info(
            "[VolcenginePolicy] lifecycle-confirm phase=plugin-initialize "
            "provider_reloads=%d ids=%s audio=%dMiB video=%dMiB image=%dMiB "
            "cache=%s/every=%d",
            len(reloaded_ids),
            ",".join(reloaded_ids) or "-",
            active_limits.audio_max_bytes // (1024 * 1024),
            active_limits.video_max_bytes // (1024 * 1024),
            active_limits.image_max_bytes // (1024 * 1024),
            cache_enabled,
            cache_every,
        )

        if changed_ids:
            logger.info(
                "Volcengine video transport migration complete: model_cards=%d; "
                "AstrBot capability feedback untouched.",
                len({provider_id for provider_id in changed_ids if provider_id}),
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
