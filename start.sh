#!/bin/bash

# Change to the app directory
cd league_tracker

# Export the app module path
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Run gunicorn (Railway installs dependencies automatically)
exec gunicorn --bind 0.0.0.0:$PORT app:app
