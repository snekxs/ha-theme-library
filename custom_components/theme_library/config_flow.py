from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_URL, DOMAIN


class ThemeLibraryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input["url"].rstrip("/")
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(
                    f"{url}/api/favorites", timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    resp.raise_for_status()
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Light Theme Library", data={"url": url})

        schema = vol.Schema({vol.Required("url", default=DEFAULT_URL): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
