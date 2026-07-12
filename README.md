# Light Theme Library

A Home Assistant **custom integration** for browsing, creating, and applying
light presets/themes across your smart lights — like Hue's built-in themes,
but extensible. Installs entirely through HACS; no separate add-on, no
Docker container, no port to publish. Everything runs inside Home Assistant
Core itself.

## What it does

- Adds a **"Themes" panel** to your sidebar — a full browsable gallery, not
  a config page.
- Ships with 96 bundled themes across 23 categories (Relax & Unwind,
  Energize & Wake Up, Focus & Work, Reading, Movie & TV, Party & Social,
  Romantic, Seasonal & Holiday, Nature & Outdoors, Gaming, Lo-Fi, Loft,
  Sci-Fi & Neon, Zen & Meditation, Coffee Shop & Cafe, Tropical & Beach,
  Retro & Vintage, Space & Galaxy, Fantasy & Magic, Botanical &
  Greenhouse, Wine & Vineyard, Baby & Nursery, Urban Night), filterable
  by category pill.
- Themes are **palettes**, not fixed scenes: a theme is a list of
  color/brightness "slots" with no hardcoded entity IDs. Slots are assigned
  round-robin across your target lights — so the same theme works on any
  room, on any instance.
- **Controls panel**: a single collapsible section holds the Target Lights
  picker (which lights themes/effects apply to) and the Dynamic Mode
  toggle.
- **Dynamic Mode**: a global on/off switch (with a speed control). When on,
  applying a theme doesn't just set your lights once — it slowly and
  continuously cycles through the theme's colors, like Hue's dynamic
  scenes, until you hit Stop or apply something else.
- **Effects**: a separate tab with 9 built-in animated effects across 4
  categories (Flames: Candle, Fireplace · Sparkly: Glisten, Sparkle ·
  Wavy: Underwater, Cosmos, Sunbeam · Loops: Prism, Opal). Always live —
  flickering, sparkling, or smoothly cycling — until stopped.
- **Create your own theme**: pick lights, set them how you want via HA,
  then hit "+ New" to capture their current color/brightness as a
  reusable theme.
- **Favorites → real buttons**: star a theme and it becomes its own
  single-button **device**, named exactly the theme (e.g. "Sunset Glow"),
  with a real `unique_id` — assignable to an area, addable to any
  dashboard, and shows with a clean name with no prefix, through HA's
  normal entity settings. (Favoriting also creates a matching HA scene as
  a byproduct, but the button is the intended way to use this — the
  scene has no such management support since `scene.create` entities
  can't have a `unique_id`.)

## Install via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=snekxs&repository=ha-theme-library&category=integration)

Click the button above (requires HACS already installed, and My Home
Assistant linked — most instances have this by default) to jump straight
to the "Add repository" dialog, prefilled. Then:

1. Click **Add** in that dialog.
2. Find "Light Theme Library" in HACS → **Install**.
3. Restart Home Assistant Core.
4. Click the button below (or **Settings → Devices & Services → Add
   Integration** → search "Light Theme Library") → Submit — no
   configuration needed.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=theme_library)

5. A "Themes" panel appears in your sidebar, and a "Light Theme Library"
   device is created — favorite a theme to get its button.

**No My Home Assistant link / prefer manual steps:** In HACS: **⋮ (top
right) → Custom repositories** → paste
`https://github.com/snekxs/ha-theme-library`, Category: **Integration** →
Add, then continue from step 2 above.

Releases are published automatically by GitHub Actions whenever a `v*`
tag is pushed (see `.github/workflows/release.yml`), so HACS always has
a proper Release to install from — no manual step needed.

**Install manually instead (no HACS):** copy `custom_components/theme_library/`
from this repo into `config/custom_components/theme_library/` on your HA
instance, then continue from step 3 above.

## How it works (architecture)

Everything lives in one `custom_components/theme_library/` integration:

- **`storage.py`** — persists themes/target-lights/settings/favorites via
  HA's own `Store` helper (in `.storage/`, same as any other integration's
  data — no separate database or files to manage).
- **`engine.py`** — applies themes/effects by calling `light.turn_on` and
  `scene.create` directly through `hass.services.async_call`, and runs the
  dynamic-cycling/effect background loops as HA-tracked async tasks.
- **`views.py`** — registers the panel's API under `/api/theme_library/*`
  using HA's `HomeAssistantView`. These require normal HA authentication
  (unlike a bare add-on API) — the panel passes its session token through
  automatically.
- **`www/`** — the actual gallery UI (plain HTML/CSS/JS), served as a
  static path and wrapped in a small custom sidebar panel (`panel.js`)
  that hands the iframe an auth token on load.
- **`button.py`** — one `ButtonEntity` per favorited theme, updated
  instantly via a dispatcher signal when you favorite/un-favorite (no
  polling).

**Known limitations:** only themes get buttons (not effects); un-favoriting
doesn't remove a theme's button, just marks it unavailable; the panel's
auth token is captured once when it loads and isn't refreshed, so if you
leave the panel open for a very long session API calls may eventually need
a page reload; and **this hasn't been tested against a live Home Assistant
instance** — the previous add-on+integration split was tested step by step
against your real instance, but this full rewrite (in-process API views,
static panel registration, service calls replacing REST) is new. If setup,
the panel, or button presses fail, please send screenshots/errors and
we'll fix it together, same as everything else so far.
