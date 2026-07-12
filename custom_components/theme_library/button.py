from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ThemeLibraryCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: ThemeLibraryCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _sync_entities() -> None:
        themes = coordinator.data.get("favorite_themes", []) if coordinator.data else []
        new_entities = []
        for theme in themes:
            if theme["id"] not in known_ids:
                known_ids.add(theme["id"])
                new_entities.append(ThemeButton(coordinator, entry, theme))
        if new_entities:
            async_add_entities(new_entities)
        # Un-favorited themes aren't removed automatically (kept simple for
        # now) — their button just becomes unavailable, see ThemeButton.available.

    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))
    _sync_entities()


class ThemeButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator: ThemeLibraryCoordinator, entry: ConfigEntry, theme: dict) -> None:
        super().__init__(coordinator)
        self._theme_id = theme["id"]
        self._attr_unique_id = f"{entry.entry_id}_{theme['id']}"
        self._attr_name = theme["name"]
        self._attr_icon = "mdi:palette"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Light Theme Library",
            manufacturer="Light Theme Library",
            model="Theme Buttons",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        favorite_ids = {t["id"] for t in self.coordinator.data.get("favorite_themes", [])}
        return self._theme_id in favorite_ids

    async def async_press(self) -> None:
        await self.coordinator.apply_theme(self._theme_id)
