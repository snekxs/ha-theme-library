#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Light Theme Library..."
cd /app || exit 1
exec python3 main.py
