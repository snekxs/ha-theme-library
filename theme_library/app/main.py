import asyncio
import json
import math
import os
import random
import re
import shutil
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get("THEME_LIBRARY_DATA_DIR", "/data"))
THEMES_FILE = DATA_DIR / "themes.json"
DEFAULT_THEMES_FILE = APP_DIR / "themes_default.json"
TARGET_LIGHTS_FILE = DATA_DIR / "target_lights.json"
EFFECTS_FILE = APP_DIR / "effects_default.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_SETTINGS = {"dynamic_mode": False, "dynamic_interval": 8}

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_API_BASE = "http://supervisor/core/api"
SUBMISSION_REPO = os.environ.get("SUBMISSION_REPO", "").strip()

ALLOWED_LIGHT_ATTRS = {"color", "brightness_pct"}

app = FastAPI(title="Light Theme Library")


def ha_headers() -> dict:
    return {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }


async def ha_get(path: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HA_API_BASE}{path}", headers=ha_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()


async def ha_post(path: str, body: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{HA_API_BASE}{path}", headers=ha_headers(), json=body, timeout=10)
        resp.raise_for_status()
        return resp.json() if resp.content else None


def load_themes() -> list:
    """Load themes, migrating in any new/changed bundled themes on top of
    whatever the user already has saved (local/imported themes untouched)."""
    defaults = json.loads(DEFAULT_THEMES_FILE.read_text())
    default_by_id = {d["id"]: d for d in defaults}

    if not THEMES_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        THEMES_FILE.write_text(json.dumps(defaults, indent=2))
        return defaults

    themes = json.loads(THEMES_FILE.read_text())
    existing_ids = {t["id"] for t in themes}
    changed = False

    merged = []
    for t in themes:
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
        save_themes(merged)

    return merged


def save_themes(themes: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    THEMES_FILE.write_text(json.dumps(themes, indent=2))


def load_target_lights() -> list:
    if not TARGET_LIGHTS_FILE.exists():
        return []
    return json.loads(TARGET_LIGHTS_FILE.read_text())


def save_target_lights(entity_ids: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_LIGHTS_FILE.write_text(json.dumps(entity_ids, indent=2))


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)
    return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}


def save_settings(settings: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "theme"


def hex_to_rgb(color: str):
    color = color.lstrip("#")
    if len(color) != 6:
        raise HTTPException(400, f"Invalid color: {color}")
    return [int(color[i:i + 2], 16) for i in (0, 2, 4)]


def validate_theme_payload(name: str, slots: list):
    if not name or not name.strip():
        raise HTTPException(400, "Theme name is required")
    if not slots:
        raise HTTPException(400, "At least one color slot is required")
    for slot in slots:
        extra = set(slot.keys()) - ALLOWED_LIGHT_ATTRS
        if extra:
            raise HTTPException(400, f"Unsupported slot attributes: {sorted(extra)}")
        if "color" not in slot:
            raise HTTPException(400, "Each slot needs a 'color'")
        hex_to_rgb(slot["color"])
        pct = slot.get("brightness_pct", 100)
        if not isinstance(pct, (int, float)) or not (0 <= pct <= 100):
            raise HTTPException(400, "brightness_pct must be 0-100")


# Single background task, since the add-on runs as one process/one event
# loop (uvicorn with no extra workers) — only one animated thing (a
# dynamically-cycling theme, or an effect) runs at a time, same as a real
# light only showing one live pattern at once.
_dynamic_task: Optional[asyncio.Task] = None
_dynamic_kind: Optional[str] = None  # "theme" or "effect"
_dynamic_name: Optional[str] = None


async def _safe_ha_post(path: str, body: dict):
    # A background cycle shouldn't die because of one flaky HA API call.
    try:
        await ha_post(path, body)
    except Exception:
        pass


async def _theme_cycle_loop(theme: dict, entity_ids: list, interval: float):
    slots = theme["slots"]
    offset = 0
    while True:
        for i, entity_id in enumerate(entity_ids):
            slot = slots[(i + offset) % len(slots)]
            rgb = hex_to_rgb(slot["color"])
            body = {
                "entity_id": entity_id,
                "rgb_color": rgb,
                "brightness_pct": slot.get("brightness_pct", 100),
                "transition": interval,
            }
            await _safe_ha_post("/services/light/turn_on", body)
        offset += 1
        await asyncio.sleep(interval)


async def _effect_loop(effect: dict, entity_ids: list):
    kind = effect["kind"]
    params = effect.get("params", {})
    tick = params.get("tick_seconds", 1)
    brightness_base = params.get("brightness_base", 55)

    if kind in ("flicker", "sparkle"):
        base_rgb = hex_to_rgb(effect["base_color"])
        swing = params.get("brightness_swing", 15)
        while True:
            for entity_id in entity_ids:
                if kind == "flicker":
                    pct = max(5, min(100, brightness_base + random.randint(-swing, swing)))
                    transition = 0.2
                else:  # sparkle
                    flash = random.random() < 0.25
                    pct = 100 if flash else max(5, brightness_base - swing)
                    transition = 0.15
                body = {
                    "entity_id": entity_id,
                    "rgb_color": base_rgb,
                    "brightness_pct": pct,
                    "transition": transition,
                }
                await _safe_ha_post("/services/light/turn_on", body)
            await asyncio.sleep(tick)
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
                body = {
                    "entity_id": entity_id,
                    "rgb_color": rgb,
                    "brightness_pct": round(pct),
                    "transition": tick,
                }
                await _safe_ha_post("/services/light/turn_on", body)
            step += 1
            await asyncio.sleep(tick)


async def _stop_dynamic():
    global _dynamic_task, _dynamic_kind, _dynamic_name
    if _dynamic_task is not None and not _dynamic_task.done():
        _dynamic_task.cancel()
        try:
            await _dynamic_task
        except asyncio.CancelledError:
            pass
    _dynamic_task = None
    _dynamic_kind = None
    _dynamic_name = None


class Slot(BaseModel):
    color: str
    brightness_pct: int = 100


class ThemeCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "Custom"
    tags: list[str] = []
    slots: list[Slot]


class CaptureRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "Custom"
    tags: list[str] = []
    entity_ids: list[str]


class ApplyRequest(BaseModel):
    entity_ids: Optional[list[str]] = None


class TargetLightsUpdate(BaseModel):
    entity_ids: list[str]


class SettingsUpdate(BaseModel):
    dynamic_mode: Optional[bool] = None
    dynamic_interval: Optional[int] = None


@app.get("/api/lights")
async def list_lights():
    states = await ha_get("/states")
    lights = [s for s in states if s["entity_id"].startswith("light.")]
    return [
        {
            "entity_id": s["entity_id"],
            "name": s.get("attributes", {}).get("friendly_name", s["entity_id"]),
            "state": s["state"],
        }
        for s in lights
    ]


@app.get("/api/target-lights")
def get_target_lights():
    return load_target_lights()


@app.post("/api/target-lights")
def set_target_lights(payload: TargetLightsUpdate):
    save_target_lights(payload.entity_ids)
    return payload.entity_ids


@app.get("/api/settings")
def get_settings():
    return load_settings()


@app.post("/api/settings")
async def update_settings(payload: SettingsUpdate):
    settings = load_settings()
    if payload.dynamic_mode is not None:
        settings["dynamic_mode"] = payload.dynamic_mode
        if not payload.dynamic_mode:
            await _stop_dynamic()
    if payload.dynamic_interval is not None:
        if not (2 <= payload.dynamic_interval <= 120):
            raise HTTPException(400, "dynamic_interval must be between 2 and 120 seconds")
        settings["dynamic_interval"] = payload.dynamic_interval
    save_settings(settings)
    return settings


@app.get("/api/dynamic/status")
def dynamic_status():
    running = _dynamic_task is not None and not _dynamic_task.done()
    return {
        "running": running,
        "kind": _dynamic_kind if running else None,
        "name": _dynamic_name if running else None,
    }


@app.post("/api/dynamic/stop")
async def stop_dynamic():
    await _stop_dynamic()
    return {"running": False}


@app.get("/api/effects")
def list_effects():
    return json.loads(EFFECTS_FILE.read_text())


@app.post("/api/effects/{effect_id}/apply")
async def apply_effect(effect_id: str, payload: ApplyRequest):
    global _dynamic_task, _dynamic_kind, _dynamic_name

    effects = json.loads(EFFECTS_FILE.read_text())
    effect = next((e for e in effects if e["id"] == effect_id), None)
    if not effect:
        raise HTTPException(404, "Effect not found")

    entity_ids = payload.entity_ids if payload.entity_ids else load_target_lights()
    if not entity_ids:
        raise HTTPException(400, "No target lights selected. Pick your target lights at the top of the page first.")

    await _stop_dynamic()
    _dynamic_task = asyncio.create_task(_effect_loop(effect, entity_ids))
    _dynamic_kind = "effect"
    _dynamic_name = effect["name"]
    return {"dynamic": True, "kind": "effect", "name": effect["name"]}


@app.get("/api/themes")
def list_themes():
    return load_themes()


@app.post("/api/themes")
def create_theme(payload: ThemeCreate):
    slots = [s.model_dump() for s in payload.slots]
    validate_theme_payload(payload.name, slots)
    themes = load_themes()
    theme = {
        "id": slugify(payload.name) + "-" + os.urandom(3).hex(),
        "name": payload.name,
        "description": payload.description,
        "category": payload.category or "Custom",
        "tags": payload.tags,
        "source": "local",
        "slots": slots,
    }
    themes.append(theme)
    save_themes(themes)
    return theme


@app.post("/api/themes/capture")
async def capture_theme(payload: CaptureRequest):
    if not payload.entity_ids:
        raise HTTPException(400, "Select at least one light to capture")
    states = await ha_get("/states")
    by_id = {s["entity_id"]: s for s in states}
    slots = []
    for entity_id in payload.entity_ids:
        state = by_id.get(entity_id)
        if not state:
            continue
        attrs = state.get("attributes", {})
        rgb = attrs.get("rgb_color")
        brightness = attrs.get("brightness")
        color = "#{:02x}{:02x}{:02x}".format(*rgb) if rgb else "#ffffff"
        pct = round((brightness / 255) * 100) if brightness else 100
        slots.append({"color": color, "brightness_pct": pct})
    if not slots:
        raise HTTPException(400, "None of the selected lights had readable state")
    validate_theme_payload(payload.name, slots)
    themes = load_themes()
    theme = {
        "id": slugify(payload.name) + "-" + os.urandom(3).hex(),
        "name": payload.name,
        "description": payload.description,
        "category": payload.category or "Custom",
        "tags": payload.tags,
        "source": "local",
        "slots": slots,
    }
    themes.append(theme)
    save_themes(themes)
    return theme


@app.post("/api/themes/{theme_id}/apply")
async def apply_theme(theme_id: str, payload: ApplyRequest):
    global _dynamic_task, _dynamic_kind, _dynamic_name

    themes = load_themes()
    theme = next((t for t in themes if t["id"] == theme_id), None)
    if not theme:
        raise HTTPException(404, "Theme not found")

    entity_ids = payload.entity_ids if payload.entity_ids else load_target_lights()
    if not entity_ids:
        raise HTTPException(400, "No target lights selected. Pick your target lights at the top of the page first.")

    settings = load_settings()
    await _stop_dynamic()

    if settings.get("dynamic_mode"):
        interval = settings.get("dynamic_interval", 8)
        _dynamic_task = asyncio.create_task(_theme_cycle_loop(theme, entity_ids, interval))
        _dynamic_kind = "theme"
        _dynamic_name = theme["name"]
        return {"dynamic": True, "kind": "theme", "name": theme["name"]}

    slots = theme["slots"]
    results = []
    for i, entity_id in enumerate(entity_ids):
        slot = slots[i % len(slots)]
        rgb = hex_to_rgb(slot["color"])
        body = {
            "entity_id": entity_id,
            "rgb_color": rgb,
            "brightness_pct": slot.get("brightness_pct", 100),
        }
        await ha_post("/services/light/turn_on", body)
        results.append(entity_id)
    return {"dynamic": False, "applied_to": results}


@app.delete("/api/themes/{theme_id}")
def delete_theme(theme_id: str):
    themes = load_themes()
    theme = next((t for t in themes if t["id"] == theme_id), None)
    if not theme:
        raise HTTPException(404, "Theme not found")
    if theme.get("source") == "bundled":
        raise HTTPException(400, "Bundled themes can't be deleted")
    themes = [t for t in themes if t["id"] != theme_id]
    save_themes(themes)
    return {"deleted": theme_id}


@app.get("/api/themes/{theme_id}/submit-url")
def submit_url(theme_id: str):
    if not SUBMISSION_REPO:
        raise HTTPException(400, "No submission_repo configured in add-on options")
    themes = load_themes()
    theme = next((t for t in themes if t["id"] == theme_id), None)
    if not theme:
        raise HTTPException(404, "Theme not found")

    submission = {
        "name": theme["name"],
        "description": theme.get("description", ""),
        "category": theme.get("category", "Custom"),
        "tags": theme.get("tags", []),
        "slots": theme["slots"],
    }
    filename = f"themes/{slugify(theme['name'])}.json"
    content = json.dumps(submission, indent=2)
    query = urllib.parse.urlencode({"filename": filename, "value": content})
    url = f"https://github.com/{SUBMISSION_REPO}/new/main?{query}"
    return {"url": url}


app.mount("/", StaticFiles(directory=str(APP_DIR / "static"), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8099)
