# Changelog

## 0.6.1

- Fixed scene pinning: the generated scene entity ID was built from the
  theme's JSON-style slug, which uses hyphens (`sunset-glow`) — not
  valid in a Home Assistant entity ID, which only allows lowercase
  letters, digits, and underscores. Scene IDs now use a proper
  HA-safe slug (`sunset_glow`), so favoriting a theme should now
  successfully create the pinnable scene.
- Pin failures now surface the actual error from Home Assistant (status
  code + message) instead of a generic "couldn't reach" message, so any
  future failure is actually diagnosable from the toast.

## 0.6.0

- Removed the Share/community-submission feature entirely: no more
  Share button, `submission_repo` option, or submit-url endpoint.
- Added **Favorites**: a star button on every theme/effect card, plus a
  "★ Favorites" filter to see just your starred items.
- Favoriting a theme now creates/updates a real Home Assistant scene
  entity (`scene.theme_library_<name>`) snapshotted onto your current
  target lights, so it can be added as a button on your own Lovelace
  dashboard.

## 0.5.1

- Candle and Fireplace flicker much more lifelike now: each light runs
  its own independent, unsynchronized flicker loop (instead of all
  lights stepping in lockstep), brightness smooths toward organic
  random targets with occasional bigger dips/flares, and color
  temperature shifts subtly warmer at dips and whiter at flares — plus
  faster, snappier ticks so it doesn't read as static.

## 0.5.0

- Added **Dynamic Mode**: a global toggle (with a speed control) that
  makes theme Apply continuously cycle colors instead of setting them
  once, until stopped or replaced.
- Added an **Effects** tab: 9 built-in animated effects (flicker,
  sparkle, slow color waves, smooth rainbow loops) across 4 categories —
  Flames, Sparkly, Wavy, Loops. Effects are always live, unlike static
  themes.
- Added a running-status banner with a one-tap Stop, shown whenever a
  theme is cycling or an effect is active.
- Condensed the UI: Target Lights and Dynamic Mode now live in one
  collapsible Controls panel (collapsed by default), category pills
  scroll horizontally instead of wrapping into a wall of pills, and
  cards/spacing are tighter on both mobile and desktop.
- Background theme-cycling/effect calls to Home Assistant now fail
  silently on transient errors instead of killing the whole cycle.

## 0.4.0

- Split "Lo-Fi & Loft" into two separate categories — **Lo-Fi** and
  **Loft** — each with their own themes.
- Added 67 new bundled themes across 13 new categories: Sci-Fi & Neon,
  Zen & Meditation, Coffee Shop & Cafe, Tropical & Beach, Retro &
  Vintage, Space & Galaxy, Fantasy & Magic, Botanical & Greenhouse, Wine
  & Vineyard, Baby & Nursery, Urban Night, plus 4 more Loft themes and 2
  more each in Gaming and Movie & TV. 96 themes total across 23
  categories now.
- Every new/changed theme was checked for color collisions against
  others in the same category before shipping.
- Already-installed instances will pick these up automatically on next
  start; your own saved themes are untouched.

## 0.3.1

- Target Lights bar is now collapsible (click the header to expand/collapse;
  state is remembered).
- Added a new "Lo-Fi & Loft" category with 5 muted/dusty themes (Lofi
  Chill, Rainy Window, Loft Industrial, Vinyl Nights, Late Study Lofi).
- Removed two near-duplicate themes (Candlelight, Cinema Glow) and
  recolored five others that were too close in color to a sibling in the
  same category (Deep Focus, Date Night, Winter Frost, Disco Night,
  Citrus Burst) — 29 themes total now.
- Already-installed instances will drop the removed themes and pick up
  the recolored/new ones automatically; your own saved themes are
  untouched either way.

## 0.3.0

- Added 20 new bundled themes (26 total) across 10 categories: Relax &
  Unwind, Energize & Wake Up, Focus & Work, Reading, Movie & TV, Party &
  Social, Romantic, Seasonal & Holiday, Nature & Outdoors, Gaming.
- Added category filter pills above the theme grid, and a Category field
  when creating your own theme.
- Existing installs automatically pick up the new/updated bundled themes
  on next start — your own saved themes are untouched.
- App background is now transparent so the Home Assistant dashboard
  background shows through instead of a fixed dark/light fill; theme
  cards and modals keep a solid background for readability.

## 0.2.1

- Added add-on icon/logo.
- Added this changelog.

## 0.2.0

- Replaced the per-theme light picker with a persistent "Target Lights"
  bar: pick your target lights once at the top of the page (saved
  automatically), then Apply fires immediately against that selection.
- New Theme capture now defaults to your saved target lights.

## 0.1.0

- Initial release.
- Browsable gallery of palette-based themes (color/brightness slots, no
  hardcoded entity IDs).
- Bundled starter themes: Relax, Energize, Concentrate, Reading, Sunset
  Glow, Movie Night.
- Create your own theme by capturing the current state of selected
  lights.
- Share a theme via a prefilled GitHub "new file" link (`submission_repo`
  option) — no token or OAuth required.
