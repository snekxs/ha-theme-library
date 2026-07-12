from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SIGNAL_ACTIVE_THEME_CHANGED, SIGNAL_FAVORITES_CHANGED
from .engine import ThemeLibraryEngine
from .storage import ThemeLibraryStorage


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    storage: ThemeLibraryStorage = data["storage"]
    engine: ThemeLibraryEngine = data["engine"]

    known_ids: set[str] = set()
    entities_by_id: dict[str, "ThemeSwitch"] = {}

    async def _sync_entities(*_args) -> None:
        favorites = await storage.async_load_favorites()
        themes = await storage.async_load_themes()
        theme_by_id = {t["id"]: t for t in themes}
        favorite_ids = set(favorites.get("themes", []))

        new_entities = []
        newly_added_ids = set()
        for theme_id in favorite_ids:
            theme = theme_by_id.get(theme_id)
            if theme and theme_id not in known_ids:
                known_ids.add(theme_id)
                newly_added_ids.add(theme_id)
                switch = ThemeSwitch(engine, entry, theme)
                entities_by_id[theme_id] = switch
                new_entities.append(switch)
        if new_entities:
            async_add_entities(new_entities)

        # Only touch entities that were already added in an earlier pass —
        # ones created just above already start favorited/available.
        for theme_id, switch in entities_by_id.items():
            if theme_id not in newly_added_ids:
                switch.set_favorited(theme_id in favorite_ids)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_FAVORITES_CHANGED, _sync_entities))
    await _sync_entities()


class ThemeSwitch(SwitchEntity):
    # Each theme gets its own single-entity device, named exactly the
    # theme, so the switch's own display name is unprefixed (see button.py
    # history in git log for why a shared device doesn't work for this).
    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:palette"

    def __init__(self, engine: ThemeLibraryEngine, entry: ConfigEntry, theme: dict) -> None:
        self._engine = engine
        self._theme_id = theme["id"]
        self._favorited = True
        self._attr_unique_id = f"{entry.entry_id}_{theme['id']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, theme["id"])},
            name=theme["name"],
            manufacturer="Light Theme Library",
            model="Theme Switch",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_ACTIVE_THEME_CHANGED, self._handle_active_changed)
        )

    @callback
    def _handle_active_changed(self) -> None:
        self.async_write_ha_state()

    def set_favorited(self, favorited: bool) -> None:
        if favorited != self._favorited:
            self._favorited = favorited
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._favorited

    @property
    def is_on(self) -> bool:
        return self._engine.is_theme_active(self._theme_id)

    async def async_turn_on(self, **kwargs) -> None:
        themes = await self._engine.storage.async_load_themes()
        theme = next((t for t in themes if t["id"] == self._theme_id), None)
        if not theme:
            return
        entity_ids = await self._engine.storage.async_load_target_lights()
        if not entity_ids:
            return
        await self._engine.apply_theme(theme, entity_ids)

    async def async_turn_off(self, **kwargs) -> None:
        entity_ids = await self._engine.storage.async_load_target_lights()
        if not entity_ids:
            return
        await self._engine.turn_off_lights(entity_ids)
