# Light Theme Library

A Home Assistant App (add-on) for browsing, creating, and applying light
presets/themes across your smart lights — like Hue's built-in themes, but
extensible and shareable.

## What it does

- Ships with 29 bundled themes across 11 categories (Relax & Unwind,
  Energize & Wake Up, Focus & Work, Reading, Movie & TV, Party & Social,
  Romantic, Seasonal & Holiday, Nature & Outdoors, Gaming, Lo-Fi & Loft),
  filterable by category pill at the top of the gallery.
- Themes are **palettes**, not fixed scenes: a theme is a list of
  color/brightness "slots" with no hardcoded entity IDs. Slots are assigned
  round-robin across your target lights — so the same theme works on any
  room, on any instance.
- **Target Lights bar**: pick which lights themes apply to once, at the top
  of the page (collapsible, so it stays out of the way once set) — the
  selection is saved automatically. Clicking a theme's **Apply** button
  fires immediately against that saved selection; no picker per click.
- **Create your own**: pick a set of lights, set them how you want via the
  HA app/dashboard, then hit "New Theme" to capture their current
  color/brightness as a reusable theme (defaults to your saved target
  lights, but you can pick different ones for the capture).
- **Share to a community repo**: hitting "Share" on a theme opens a
  prefilled GitHub "create new file" page (via the `submission_repo`
  option) with the theme's JSON pre-filled, so you (or anyone) can review
  and open a PR — no GitHub token or OAuth wired into the add-on itself.

## Install via the published repository (recommended)

1. In Home Assistant: **Settings → Apps → App Store → ⋮ → Repositories**
   (older versions: **Settings → Add-ons → Add-on Store**), paste
   `https://github.com/snekxs/ha-theme-library`, save.
2. "Light Theme Library" appears in the store; install as normal.
3. Start it and enable "Show in sidebar" — it uses ingress, so it opens
   inside the HA UI with no extra port/auth setup.

For a one-click add flow, generate a `my.home-assistant.io` add-repository
link pointing at that URL and share that instead of raw instructions.

## Configuration

In the add-on's **Configuration** tab:

- `submission_repo` (optional): a GitHub `owner/repo` (e.g.
  `yourname/ha-theme-library-submissions`) that has a `themes/` folder on
  its default branch. When set, the "Share" button on any theme opens a
  prefilled GitHub page to submit that theme as a new file/PR there. Leave
  blank to disable sharing.

## Security notes

- Runs with `homeassistant_api: true` and `hassio_role: homeassistant`
  only — enough to read light states and call `light.turn_on`, nothing
  more (no `admin` role, no host network, protection mode stays enabled).
- The "Share" feature never holds a GitHub token or writes to GitHub on
  your behalf — it only builds a URL. The actual commit/PR happens in your
  browser, authenticated as you.
- Submitted theme files should be treated as untrusted input by whoever
  reviews `submission_repo`'s PRs: only `color`/`brightness_pct` fields are
  ever written by this app, and a reviewer should reject anything that
  doesn't match that shape before merging.
