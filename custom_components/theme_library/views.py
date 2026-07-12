from __future__ import annotations

import os

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import engine as engine_module
from .const import DOMAIN, SIGNAL_FAVORITES_CHANGED


def _get(hass: HomeAssistant):
    data = hass.data[DOMAIN]
    return data["engine"], data["storage"]


async def _json_body(request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


class LightsView(HomeAssistantView):
    url = "/api/theme_library/lights"
    name = "api:theme_library:lights"

    async def get(self, request):
        hass = request.app["hass"]
        states = hass.states.async_all("light")
        lights = [
            {
                "entity_id": s.entity_id,
                "name": s.attributes.get("friendly_name", s.entity_id),
                "state": s.state,
            }
            for s in states
        ]
        return self.json(lights)


class TargetLightsView(HomeAssistantView):
    url = "/api/theme_library/target-lights"
    name = "api:theme_library:target_lights"

    async def get(self, request):
        _, storage = _get(request.app["hass"])
        return self.json(await storage.async_load_target_lights())

    async def post(self, request):
        _, storage = _get(request.app["hass"])
        body = await _json_body(request)
        entity_ids = body.get("entity_ids", [])
        await storage.async_save_target_lights(entity_ids)
        return self.json(entity_ids)


class SettingsView(HomeAssistantView):
    url = "/api/theme_library/settings"
    name = "api:theme_library:settings"

    async def get(self, request):
        _, storage = _get(request.app["hass"])
        return self.json(await storage.async_load_settings())

    async def post(self, request):
        engine, storage = _get(request.app["hass"])
        body = await _json_body(request)
        settings = await storage.async_load_settings()

        if body.get("dynamic_mode") is not None:
            settings["dynamic_mode"] = bool(body["dynamic_mode"])
            if not settings["dynamic_mode"]:
                await engine.stop_dynamic()

        if body.get("dynamic_interval") is not None:
            interval = int(body["dynamic_interval"])
            if not (2 <= interval <= 120):
                return self.json({"detail": "dynamic_interval must be between 2 and 120 seconds"}, status_code=400)
            settings["dynamic_interval"] = interval

        await storage.async_save_settings(settings)
        return self.json(settings)


class DynamicStatusView(HomeAssistantView):
    url = "/api/theme_library/dynamic/status"
    name = "api:theme_library:dynamic_status"

    async def get(self, request):
        engine, _ = _get(request.app["hass"])
        return self.json(engine.dynamic_status())


class DynamicStopView(HomeAssistantView):
    url = "/api/theme_library/dynamic/stop"
    name = "api:theme_library:dynamic_stop"

    async def post(self, request):
        engine, _ = _get(request.app["hass"])
        await engine.stop_dynamic()
        return self.json({"running": False})


class EffectsView(HomeAssistantView):
    url = "/api/theme_library/effects"
    name = "api:theme_library:effects"

    async def get(self, request):
        _, storage = _get(request.app["hass"])
        return self.json(storage.load_effects())


class EffectApplyView(HomeAssistantView):
    url = "/api/theme_library/effects/{effect_id}/apply"
    name = "api:theme_library:effect_apply"

    async def post(self, request, effect_id):
        engine, storage = _get(request.app["hass"])
        effects = storage.load_effects()
        effect = next((e for e in effects if e["id"] == effect_id), None)
        if not effect:
            return self.json({"detail": "Effect not found"}, status_code=404)

        body = await _json_body(request)
        entity_ids = body.get("entity_ids") or await storage.async_load_target_lights()
        if not entity_ids:
            return self.json(
                {"detail": "No target lights selected. Pick your target lights first."}, status_code=400
            )

        result = await engine.apply_effect(effect, entity_ids)
        return self.json(result)


class ThemesView(HomeAssistantView):
    url = "/api/theme_library/themes"
    name = "api:theme_library:themes"

    async def get(self, request):
        _, storage = _get(request.app["hass"])
        return self.json(await storage.async_load_themes())

    async def post(self, request):
        _, storage = _get(request.app["hass"])
        body = await _json_body(request)
        name = body.get("name", "")
        slots = body.get("slots", [])
        try:
            engine_module.validate_theme_payload(name, slots)
        except ValueError as e:
            return self.json({"detail": str(e)}, status_code=400)

        themes = await storage.async_load_themes()
        theme = {
            "id": engine_module.slugify(name) + "-" + os.urandom(3).hex(),
            "name": name,
            "description": body.get("description", ""),
            "category": body.get("category") or "Custom",
            "tags": body.get("tags", []),
            "source": "local",
            "slots": slots,
        }
        themes.append(theme)
        await storage.async_save_themes(themes)
        return self.json(theme)


class ThemeCaptureView(HomeAssistantView):
    url = "/api/theme_library/themes/capture"
    name = "api:theme_library:theme_capture"

    async def post(self, request):
        hass = request.app["hass"]
        _, storage = _get(hass)
        body = await _json_body(request)
        entity_ids = body.get("entity_ids", [])
        if not entity_ids:
            return self.json({"detail": "Select at least one light to capture"}, status_code=400)

        slots = []
        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            if not state:
                continue
            attrs = state.attributes
            rgb = attrs.get("rgb_color")
            brightness = attrs.get("brightness")
            color = "#{:02x}{:02x}{:02x}".format(*rgb) if rgb else "#ffffff"
            pct = round((brightness / 255) * 100) if brightness else 100
            slots.append({"color": color, "brightness_pct": pct})

        if not slots:
            return self.json({"detail": "None of the selected lights had readable state"}, status_code=400)

        name = body.get("name", "")
        try:
            engine_module.validate_theme_payload(name, slots)
        except ValueError as e:
            return self.json({"detail": str(e)}, status_code=400)

        themes = await storage.async_load_themes()
        theme = {
            "id": engine_module.slugify(name) + "-" + os.urandom(3).hex(),
            "name": name,
            "description": body.get("description", ""),
            "category": body.get("category") or "Custom",
            "tags": body.get("tags", []),
            "source": "local",
            "slots": slots,
        }
        themes.append(theme)
        await storage.async_save_themes(themes)
        return self.json(theme)


class ThemeApplyView(HomeAssistantView):
    url = "/api/theme_library/themes/{theme_id}/apply"
    name = "api:theme_library:theme_apply"

    async def post(self, request, theme_id):
        engine, storage = _get(request.app["hass"])
        themes = await storage.async_load_themes()
        theme = next((t for t in themes if t["id"] == theme_id), None)
        if not theme:
            return self.json({"detail": "Theme not found"}, status_code=404)

        body = await _json_body(request)
        entity_ids = body.get("entity_ids") or await storage.async_load_target_lights()
        if not entity_ids:
            return self.json(
                {"detail": "No target lights selected. Pick your target lights at the top of the page first."},
                status_code=400,
            )

        result = await engine.apply_theme(theme, entity_ids)
        return self.json(result)


class ThemeDeleteView(HomeAssistantView):
    url = "/api/theme_library/themes/{theme_id}"
    name = "api:theme_library:theme_delete"

    async def delete(self, request, theme_id):
        _, storage = _get(request.app["hass"])
        themes = await storage.async_load_themes()
        theme = next((t for t in themes if t["id"] == theme_id), None)
        if not theme:
            return self.json({"detail": "Theme not found"}, status_code=404)
        if theme.get("source") == "bundled":
            return self.json({"detail": "Bundled themes can't be deleted"}, status_code=400)
        themes = [t for t in themes if t["id"] != theme_id]
        await storage.async_save_themes(themes)
        return self.json({"deleted": theme_id})


class FavoritesView(HomeAssistantView):
    url = "/api/theme_library/favorites"
    name = "api:theme_library:favorites"

    async def get(self, request):
        _, storage = _get(request.app["hass"])
        return self.json(await storage.async_load_favorites())


class FavoriteToggleView(HomeAssistantView):
    url = "/api/theme_library/favorites/{kind}/{item_id}/toggle"
    name = "api:theme_library:favorite_toggle"

    async def post(self, request, kind, item_id):
        hass = request.app["hass"]
        engine, storage = _get(hass)
        if kind not in ("themes", "effects"):
            return self.json({"detail": "Unknown favorites kind"}, status_code=404)

        favorites = await storage.async_load_favorites()
        now_favorited = item_id not in favorites[kind]
        if now_favorited:
            favorites[kind].append(item_id)
        else:
            favorites[kind].remove(item_id)
        await storage.async_save_favorites(favorites)

        if kind == "themes":
            async_dispatcher_send(hass, SIGNAL_FAVORITES_CHANGED)

        result = {"favorited": now_favorited, "pinned": False, "scene_entity_id": None}

        if kind == "themes" and now_favorited:
            themes = await storage.async_load_themes()
            theme = next((t for t in themes if t["id"] == item_id), None)
            if theme:
                try:
                    scene_entity_id = await engine.pin_theme_scene(theme)
                    result["pinned"] = True
                    result["scene_entity_id"] = scene_entity_id
                except ValueError as e:
                    result["pin_error"] = str(e)
                except Exception as e:
                    result["pin_error"] = f"Home Assistant rejected the scene: {e}"

        return self.json(result)


def all_views() -> list:
    return [
        LightsView(),
        TargetLightsView(),
        SettingsView(),
        DynamicStatusView(),
        DynamicStopView(),
        EffectsView(),
        EffectApplyView(),
        ThemesView(),
        ThemeCaptureView(),
        ThemeApplyView(),
        ThemeDeleteView(),
        FavoritesView(),
        FavoriteToggleView(),
    ]
