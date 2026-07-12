from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class ThemeLibraryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, url: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.url = url.rstrip("/")
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict:
        try:
            async with self._session.get(
                f"{self.url}/api/favorites", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp.raise_for_status()
                favorites = await resp.json()
            async with self._session.get(
                f"{self.url}/api/themes", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp.raise_for_status()
                themes = await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Error talking to Light Theme Library add-on: {err}") from err

        theme_by_id = {t["id"]: t for t in themes}
        favorite_themes = [
            theme_by_id[tid] for tid in favorites.get("themes", []) if tid in theme_by_id
        ]
        return {"favorite_themes": favorite_themes}

    async def apply_theme(self, theme_id: str) -> None:
        async with self._session.post(
            f"{self.url}/api/themes/{theme_id}/apply",
            json={},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
