#!/usr/bin/with-contenv bashio

export SUBMISSION_REPO
SUBMISSION_REPO=$(bashio::config 'submission_repo')

bashio::log.info "Starting Light Theme Library..."
cd /app || exit 1
exec python3 main.py
