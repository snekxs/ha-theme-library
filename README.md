# Light Theme Library

A Home Assistant App (add-on) for browsing, creating, and applying light
presets/themes across your smart lights — like Hue's built-in themes, but
extensible and shareable.

## What it does

- Ships with a handful of bundled themes (Relax, Energize, Concentrate,
  Reading, Sunset Glow, Movie Night).
- Themes are **palettes**, not fixed scenes: a theme is a list of
  color/brightness "slots" with no hardcoded entity IDs. When you apply a
  theme you pick which lights to apply it to, and slots are assigned
  round-robin across your selection — so the same theme works on any room,
  on any instance.
- **Create your own**: pick a set of lights, set them how you want via the
  HA app/dashboard, then hit "New Theme" to capture their current
  color/brightness as a reusable theme.
- **Share to a community repo**: hitting "Share" on a theme opens a
  prefilled GitHub "create new file" page (via the `submission_repo`
  option) with the theme's JSON pre-filled, so you (or anyone) can review
  and open a PR — no GitHub token or OAuth wired into the add-on itself.

## Install (local development / personal use)

1. Enable the Samba or SSH add-on on your Home Assistant instance so you
   can reach the `/addons` folder.
2. Copy this repo's `theme_library/` folder into `/addons/theme_library`
   on your HA instance (so the path is
   `/addons/theme_library/config.yaml`, etc).
3. In Home Assistant: **Settings → Apps → App Store** (older versions:
   **Settings → Add-ons → Add-on Store**), click the refresh/overflow menu
   to check for local apps, and "Light Theme Library" should appear under
   Local.
4. Install, start it, and enable "Show in sidebar" — it uses ingress, so
   it opens inside the HA UI with no extra port/auth setup.

## Install via a published repository (once you push this to GitHub)

1. Push this repo to GitHub (it already has the `repository.yaml` a
   repository needs at its root).
2. In Home Assistant: **Settings → Apps → App Store → ⋮ → Repositories**,
   paste your repo's URL, save.
3. "Light Theme Library" will appear in the store; install as normal.

For a one-click add flow, generate a `my.home-assistant.io` add-repository
link pointing at your GitHub URL and share that instead of raw instructions.

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

## Local development (without Home Assistant)

```bash
cd theme_library/app
pip install -r requirements.txt
THEME_LIBRARY_DATA_DIR=./data SUPERVISOR_TOKEN=dummy python main.py
```

Note: without a real `SUPERVISOR_TOKEN` and Supervisor proxy, the
`/api/lights`, capture, and apply endpoints will fail since there's no
Home Assistant to talk to — but the static UI will load and you can
inspect `themes.json` creation.
