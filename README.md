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
  (`scene.tl_<name>`), snapshotted onto your current target lights, so
  you can add it as a one-tap button on your own Lovelace dashboard
  (**Edit Dashboard → Add Card → Entity/Button**, pick the scene).
  Un-favoriting just removes the bookmark — the scene entity is left in
  place since it's harmless and cheap to keep.
  - **One-time cleanup HA makes you do**: scenes created this way
    (via the `scene.create` service) aren't in HA's entity registry, so
    HA shows a raw, ugly name/generic icon instead of the theme's actual
    name. Open the scene's entity dialog and tap the **⚙ gear icon** to
    give it a proper name/icon — this is a normal HA thing for any
    dynamically-created entity, not specific to this app, and it's a
    one-time fix that persists.

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
