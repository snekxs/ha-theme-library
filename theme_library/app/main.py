import json
import os
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
        latest = default_by_id.get(t["id"])
        if t.get("source") == "bundled" and latest is not None:
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
    themes = load_themes()
    theme = next((t for t in themes if t["id"] == theme_id), None)
    if not theme:
        raise HTTPException(404, "Theme not found")

    entity_ids = payload.entity_ids if payload.entity_ids else load_target_lights()
    if not entity_ids:
        raise HTTPException(400, "No target lights selected. Pick your target lights at the top of the page first.")

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
    return {"applied_to": results}


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
