DOMAIN = "theme_library"
# Home Assistant Core runs with host networking in HAOS/Supervised setups,
# so it can't resolve add-on container hostnames on Supervisor's internal
# bridge network — it reaches the add-on's published port via localhost.
DEFAULT_URL = "http://localhost:8099"
SCAN_INTERVAL_SECONDS = 30
