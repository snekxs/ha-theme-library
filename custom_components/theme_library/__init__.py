from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .engine import ThemeLibraryEngine
from .storage import ThemeLibraryStorage
from .views import all_views

PLATFORMS = ["button"]
WWW_DIR = Path(__file__).parent / "www"


async def _async_register_static_path(hass: HomeAssistant, url_path: str, path: str) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths([StaticPathConfig(url_path, path, False)])
    except ImportError:
        # Older HA versions: register_static_path is synchronous.
        hass.http.register_static_path(url_path, path, False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    storage = ThemeLibraryStorage(hass)
    engine = ThemeLibraryEngine(hass, storage)
    hass.data[DOMAIN][entry.entry_id] = {"storage": storage, "engine": engine}
    # Views resolve the "active" storage/engine via these — only one config
    # entry is supported at a time, enforced in config_flow.
    hass.data[DOMAIN]["storage"] = storage
    hass.data[DOMAIN]["engine"] = engine

    if not hass.data[DOMAIN].get("_http_registered"):
        for view in all_views():
            hass.http.register_view(view)
        await _async_register_static_path(hass, "/theme_library_static", str(WWW_DIR))
        hass.data[DOMAIN]["_http_registered"] = True

    if not hass.data[DOMAIN].get("_panel_registered"):
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="Themes",
            sidebar_icon="mdi:palette",
            frontend_url_path=DOMAIN,
            config={
                "_panel_custom": {
                    "name": "theme-library-panel",
                    "js_url": "/theme_library_static/panel.js",
                    "embed_iframe": False,
                    "trust_external": False,
                }
            },
            require_admin=False,
        )
        hass.data[DOMAIN]["_panel_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data:
            await entry_data["engine"].stop_dynamic()
        if hass.data[DOMAIN].get("_panel_registered"):
            async_remove_panel(hass, DOMAIN)
            hass.data[DOMAIN]["_panel_registered"] = False
    return unload_ok
