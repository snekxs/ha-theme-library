from __future__ import annotations

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
APP_DIR = Path(__file__).parent

DEFAULT_SETTINGS = {"dynamic_mode": False, "dynamic_interval": 8}
DEFAULT_FAVORITES = {"themes": [], "effects": []}


def _load_bundled_json(filename: str):
    return json.loads((APP_DIR / filename).read_text())


class ThemeLibraryStorage:
    """Wraps HA's Store helper for all of the integration's persisted data.

    Bundled themes/effects ship as JSON files in this folder; everything a
    user creates or changes (local themes, target lights, settings,
    favorites) lives in HA's own .storage directory via Store.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._themes_store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_themes")
        self._target_lights_store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_target_lights")
        self._settings_store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_settings")
        self._favorites_store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_favorites")
        self._effects_cache: list | None = None

    # --- Themes: bundled defaults + user local/imported, migrated in place ---

    async def async_load_themes(self) -> list:
        defaults = await self.hass.async_add_executor_job(_load_bundled_json, "themes_default.json")
        default_by_id = {d["id"]: d for d in defaults}

        stored = await self._themes_store.async_load()
        if stored is None:
            await self._themes_store.async_save(defaults)
            return defaults

        existing_ids = {t["id"] for t in stored}
        changed = False
        merged = []
        for t in stored:
            if t.get("source") == "bundled":
                latest = default_by_id.get(t["id"])
                if latest is None:
                    # Bundled theme was removed upstream; drop it too.
                    changed = True
                    continue
                merged.append(latest)
                changed = changed or latest != t
            else:
                merged.append(t)

        for d in defaults:
            if d["id"] not in existing_ids:
                merged.append(d)
                changed = True

        if changed:
            await self._themes_store.async_save(merged)

        return merged

    async def async_save_themes(self, themes: list) -> None:
        await self._themes_store.async_save(themes)

    # --- Effects: bundled, read-only ---

    async def async_load_effects(self) -> list:
        if self._effects_cache is None:
            self._effects_cache = await self.hass.async_add_executor_job(
                _load_bundled_json, "effects_default.json"
            )
        return self._effects_cache

    # --- Target lights ---

    async def async_load_target_lights(self) -> list:
        return await self._target_lights_store.async_load() or []

    async def async_save_target_lights(self, entity_ids: list) -> None:
        await self._target_lights_store.async_save(entity_ids)

    # --- Settings ---

    async def async_load_settings(self) -> dict:
        stored = await self._settings_store.async_load()
        return {**DEFAULT_SETTINGS, **(stored or {})}

    async def async_save_settings(self, settings: dict) -> None:
        await self._settings_store.async_save(settings)

    # --- Favorites ---

    async def async_load_favorites(self) -> dict:
        stored = await self._favorites_store.async_load()
        return {**DEFAULT_FAVORITES, **(stored or {})}

    async def async_save_favorites(self, favorites: dict) -> None:
        await self._favorites_store.async_save(favorites)
