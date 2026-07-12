from __future__ import annotations

import asyncio
import math
import random
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_ACTIVE_THEME_CHANGED
from .storage import ThemeLibraryStorage

ALLOWED_LIGHT_ATTRS = {"color", "brightness_pct"}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "theme"


def ha_slug(name: str) -> str:
    """Slugify for use inside an HA entity_id (object_id part), which only
    allows lowercase letters, digits, and underscores — no hyphens."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "theme"


def hex_to_rgb(color: str) -> list[int]:
    color = color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Invalid color: {color}")
    return [int(color[i:i + 2], 16) for i in (0, 2, 4)]


def validate_theme_payload(name: str, slots: list) -> None:
    if not name or not name.strip():
        raise ValueError("Theme name is required")
    if not slots:
        raise ValueError("At least one color slot is required")
    for slot in slots:
        extra = set(slot.keys()) - ALLOWED_LIGHT_ATTRS
        if extra:
            raise ValueError(f"Unsupported slot attributes: {sorted(extra)}")
        if "color" not in slot:
            raise ValueError("Each slot needs a 'color'")
        hex_to_rgb(slot["color"])
        pct = slot.get("brightness_pct", 100)
        if not isinstance(pct, (int, float)) or not (0 <= pct <= 100):
            raise ValueError("brightness_pct must be 0-100")


def _shift_warmth(rgb: list, ratio: float) -> list:
    """Nudge a color redder when dim (ratio<1) or whiter when bright (ratio>1),
    mimicking how a real flame shifts color temperature as it flickers."""
    r, g, b = rgb
    if ratio < 1:
        factor = 1 - min(1.0, 1 - ratio) * 0.35
        g = g * factor
        b = b * factor * 0.7
    elif ratio > 1:
        boost = min(1.0, ratio - 1) * 0.3
        g = g + (255 - g) * boost
        b = b + (255 - b) * boost * 0.6
    return [max(0, min(255, round(v))) for v in (r, g, b)]


class ThemeLibraryEngine:
    """Applies themes/effects to lights and manages the single background
    cycling task (a dynamically-cycling theme, or a live effect) — only one
    animated thing runs at a time, same as a real light showing one pattern."""

    def __init__(self, hass: HomeAssistant, storage: ThemeLibraryStorage) -> None:
        self.hass = hass
        self.storage = storage
        self._dynamic_task: asyncio.Task | None = None
        self._dynamic_kind: str | None = None
        self._dynamic_name: str | None = None
        self._active_theme_id: str | None = None

    def is_theme_active(self, theme_id: str) -> bool:
        return self._active_theme_id == theme_id

    def _set_active_theme(self, theme_id: str | None) -> None:
        if theme_id != self._active_theme_id:
            self._active_theme_id = theme_id
            async_dispatcher_send(self.hass, SIGNAL_ACTIVE_THEME_CHANGED)

    async def _turn_on(self, entity_id: str, rgb: list, brightness_pct: int, transition: float | None = None) -> None:
        data = {"entity_id": entity_id, "rgb_color": rgb, "brightness_pct": brightness_pct}
        if transition is not None:
            data["transition"] = transition
        await self.hass.services.async_call("light", "turn_on", data, blocking=True)

    async def _safe_turn_on(self, entity_id: str, rgb: list, brightness_pct: int, transition: float | None = None) -> None:
        try:
            await self._turn_on(entity_id, rgb, brightness_pct, transition)
        except Exception:
            pass  # a background cycle shouldn't die because of one flaky call

    # --- dynamic task lifecycle ---

    async def stop_dynamic(self) -> None:
        if self._dynamic_task is not None and not self._dynamic_task.done():
            self._dynamic_task.cancel()
            try:
                await self._dynamic_task
            except asyncio.CancelledError:
                pass
        self._dynamic_task = None
        self._dynamic_kind = None
        self._dynamic_name = None

    def dynamic_status(self) -> dict:
        running = self._dynamic_task is not None and not self._dynamic_task.done()
        return {
            "running": running,
            "kind": self._dynamic_kind if running else None,
            "name": self._dynamic_name if running else None,
        }

    # --- theme dynamic cycling ---

    async def _theme_cycle_loop(self, theme: dict, entity_ids: list, interval: float) -> None:
        slots = theme["slots"]
        offset = 0
        while True:
            for i, entity_id in enumerate(entity_ids):
                slot = slots[(i + offset) % len(slots)]
                rgb = hex_to_rgb(slot["color"])
                await self._safe_turn_on(entity_id, rgb, slot.get("brightness_pct", 100), interval)
            offset += 1
            await asyncio.sleep(interval)

    # --- effect loops ---

    async def _flicker_light_loop(self, entity_id: str, base_rgb: list, brightness_base: int, swing: int, tick: float) -> None:
        level = float(brightness_base)
        while True:
            if random.random() < 0.15:
                delta = random.choice((-1, 1)) * random.uniform(swing * 1.4, swing * 2.2)
            else:
                delta = random.uniform(-swing, swing)
            target = brightness_base + delta
            level = level * 0.4 + target * 0.6  # smooth toward target, not a hard jump
            pct = max(4, min(100, round(level)))
            ratio = pct / max(brightness_base, 1)
            rgb = _shift_warmth(base_rgb, ratio)
            await self._safe_turn_on(entity_id, rgb, pct, 0.1)
            await asyncio.sleep(max(0.08, tick + random.uniform(-tick * 0.4, tick * 0.4)))

    async def _sparkle_light_loop(self, entity_id: str, base_rgb: list, brightness_base: int, swing: int, tick: float) -> None:
        while True:
            flash = random.random() < 0.25
            pct = 100 if flash else max(4, brightness_base - swing)
            rgb = _shift_warmth(base_rgb, 1.3 if flash else 0.9)
            await self._safe_turn_on(entity_id, rgb, pct, 0.1 if flash else 0.2)
            await asyncio.sleep(max(0.08, tick + random.uniform(-tick * 0.4, tick * 0.4)))

    async def _effect_loop(self, effect: dict, entity_ids: list) -> None:
        kind = effect["kind"]
        params = effect.get("params", {})
        tick = params.get("tick_seconds", 1)
        brightness_base = params.get("brightness_base", 55)

        if kind in ("flicker", "sparkle"):
            base_rgb = hex_to_rgb(effect["base_color"])
            swing = params.get("brightness_swing", 15)
            loop_fn = self._flicker_light_loop if kind == "flicker" else self._sparkle_light_loop
            await asyncio.gather(
                *(loop_fn(entity_id, base_rgb, brightness_base, swing, tick) for entity_id in entity_ids)
            )
        else:  # "wave" or "loop"
            colors = effect["colors"]
            swing = params.get("brightness_swing", 0)
            step = 0
            while True:
                for i, entity_id in enumerate(entity_ids):
                    rgb = hex_to_rgb(colors[(i + step) % len(colors)])
                    pct = brightness_base
                    if swing:
                        pct = max(5, min(100, brightness_base + swing * math.sin(step / 3)))
                    await self._safe_turn_on(entity_id, rgb, round(pct), tick)
                step += 1
                await asyncio.sleep(tick)

    # --- public entry points ---

    async def apply_theme(self, theme: dict, entity_ids: list) -> dict:
        settings = await self.storage.async_load_settings()
        await self.stop_dynamic()
        self._set_active_theme(theme["id"])

        if settings.get("dynamic_mode"):
            interval = settings.get("dynamic_interval", 8)
            self._dynamic_task = self.hass.async_create_task(
                self._theme_cycle_loop(theme, entity_ids, interval)
            )
            self._dynamic_kind = "theme"
            self._dynamic_name = theme["name"]
            return {"dynamic": True, "kind": "theme", "name": theme["name"]}

        slots = theme["slots"]
        results = []
        for i, entity_id in enumerate(entity_ids):
            slot = slots[i % len(slots)]
            rgb = hex_to_rgb(slot["color"])
            await self._turn_on(entity_id, rgb, slot.get("brightness_pct", 100))
            results.append(entity_id)
        return {"dynamic": False, "applied_to": results}

    async def apply_effect(self, effect: dict, entity_ids: list) -> dict:
        await self.stop_dynamic()
        self._set_active_theme(None)
        self._dynamic_task = self.hass.async_create_task(self._effect_loop(effect, entity_ids))
        self._dynamic_kind = "effect"
        self._dynamic_name = effect["name"]
        return {"dynamic": True, "kind": "effect", "name": effect["name"]}

    async def pin_theme_scene(self, theme: dict) -> str:
        """Create/update a real HA scene entity for this theme, snapshotted
        onto the current target lights, so it can be added as a dashboard
        button (via the button entities this integration also provides)."""
        entity_ids = await self.storage.async_load_target_lights()
        if not entity_ids:
            raise ValueError("No target lights selected. Pick your target lights first, then favorite again.")

        slots = theme["slots"]
        entities = {}
        for i, entity_id in enumerate(entity_ids):
            slot = slots[i % len(slots)]
            rgb = hex_to_rgb(slot["color"])
            brightness_255 = round(slot.get("brightness_pct", 100) / 100 * 255)
            entities[entity_id] = {"state": "on", "rgb_color": rgb, "brightness": brightness_255}

        scene_id = f"tl_{ha_slug(theme['name'])}"
        await self.hass.services.async_call(
            "scene", "create", {"scene_id": scene_id, "entities": entities}, blocking=True
        )
        return f"scene.{scene_id}"
