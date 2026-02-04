#!/bin/bash

# Run gunicorn from the root of the repo
cd /app

# Use full module path with thread workers for Flask
exec gunicorn --bind 0.0.0.0:$PORT league_tracker.app:app --workers 4 --threads 4 --timeout 120