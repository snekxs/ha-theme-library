# Light Theme Library

A Home Assistant App (add-on) for browsing, creating, and applying light
presets/themes across your smart lights — like Hue's built-in themes, but
extensible.

## What it does

- Ships with 96 bundled themes across 23 categories (Relax & Unwind,
  Energize & Wake Up, Focus & Work, Reading, Movie & TV, Party & Social,
  Romantic, Seasonal & Holiday, Nature & Outdoors, Gaming, Lo-Fi, Loft,
  Sci-Fi & Neon, Zen & Meditation, Coffee Shop & Cafe, Tropical & Beach,
  Retro & Vintage, Space & Galaxy, Fantasy & Magic, Botanical &
  Greenhouse, Wine & Vineyard, Baby & Nursery, Urban Night), filterable
  by category pill at the top of the gallery.
- Themes are **palettes**, not fixed scenes: a theme is a list of
  color/brightness "slots" with no hardcoded entity IDs. Slots are assigned
  round-robin across your target lights — so the same theme works on any
  room, on any instance.
- **Controls panel**: a single collapsible panel holds the Target Lights
  picker (which lights themes/effects apply to, saved automatically) and
  the Dynamic Mode toggle — collapsed by default to keep the page compact.
- **Dynamic Mode**: a global on/off switch (with a speed control). When
  on, applying a theme doesn't just set your lights once — it slowly and
  continuously cycles through the theme's colors, like Hue's dynamic
  scenes, until you hit Stop or apply something else. When off, Apply is
  a one-shot static set.
- **Effects**: a separate tab with 9 built-in animated effects across 4
  categories (Flames: Candle, Fireplace · Sparkly: Glisten, Sparkle ·
  Wavy: Underwater, Cosmos, Sunbeam · Loops: Prism, Opal). Unlike themes,
  effects are always live — flickering, sparkling, or smoothly cycling —
  until stopped.
- A slim banner appears at the top whenever a theme is cycling or an
  effect is running, with a one-tap **Stop**.
- **Create your own theme**: pick a set of lights, set them how you want
  via the HA app/dashboard, then hit "+ New" to capture their current
  color/brightness as a reusable theme (defaults to your saved target
  lights, but you can pick different ones for the capture).
- **Favorites**: star any theme or effect to bookmark it — a "★
  Favorites" filter shows just your starred items. Favoriting a *theme*
  also creates/updates a real Home Assistant scene entity
  (`scene.tl_<name>`), snapshotted onto your current target lights.
  You *can* add this straight to your dashboard (**Edit Dashboard → Add
  Card → Button**, pick the scene, and set a Name/Icon in the card's own
  editor — the entity itself can't be renamed since `scene.create`
  entities have no `unique_id`), but for real, fully-manageable buttons
  see the companion integration below.

## Companion integration: real buttons for your favorites

The add-on's Favorites scenes work, but Home Assistant can't manage
their name/icon/area since they lack a `unique_id` (a `scene.create`
limitation, not fixable from the add-on side). `custom_components/theme_library/`
is a small companion **integration** that fixes this properly: it polls
the add-on for your favorited themes and exposes each one as a real
`button` entity under a "Light Theme Library" **device** — fully
renameable, assignable to an area, and pressable from any dashboard,
the same as any other HA entity.

**Install via HACS (recommended — entirely from GitHub, no file copying):**

1. In HACS: **⋮ (top right) → Custom repositories** → paste
   `https://github.com/snekxs/ha-theme-library`, Category: **Integration**
   → Add.
2. Find "Light Theme Library" in HACS → **Install**.
3. Restart Home Assistant Core (Settings → System → Restart, not the
   add-on).
4. **Settings → Devices & Services → Add Integration** → search "Light
   Theme Library" → accept the default URL (works as long as the
   add-on's slug is unchanged) → Submit.
5. A "Light Theme Library" device appears with one button per favorited
   theme. Add them to your dashboard, rename/re-icon them, assign an
   area — all through HA's normal entity settings.

The repo is tagged (`v0.1.0`) for HACS, but doesn't have a formal
GitHub *Release* published yet (that's a manual step on GitHub's
website — Releases → Draft a new release → pick the `v0.1.0` tag →
Publish). If HACS refuses to install without one, do that first.

**Install manually instead (no HACS):**

1. Copy `custom_components/theme_library/` from this repo into
   `config/custom_components/theme_library/` on your HA instance (same
   Samba/SSH access as the add-on).
2. Continue from step 3 above (restart Core, Add Integration).

**Current limitations:** only themes get buttons (not effects); un-favoriting
a theme doesn't remove its button, just marks it unavailable; and this
hasn't been tested against a live Home Assistant instance yet — if
setup or button presses fail, the error should point at what's wrong
(usually connectivity to the add-on), but please report back what you
see.

## Install via the published repository (recommended)

1. In Home Assistant: **Settings → Apps → App Store → ⋮ → Repositories**
   (older versions: **Settings → Add-ons → Add-on Store**), paste
   `https://github.com/snekxs/ha-theme-library`, save.
2. "Light Theme Library" appears in the store; install as normal.
3. Start it and enable "Show in sidebar" — it uses ingress, so it opens
   inside the HA UI with no extra port/auth setup.

For a one-click add flow, generate a `my.home-assistant.io` add-repository
link pointing at that URL and share that instead of raw instructions.

## Security notes

- Runs with `homeassistant_api: true` and `hassio_role: homeassistant`
  only — enough to read light states, call `light.turn_on`, and create
  scenes via `scene.create` (used by Favorites). No `admin` role, no host
  network, protection mode stays enabled.
