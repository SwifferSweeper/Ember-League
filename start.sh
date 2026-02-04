#!/bin/bash

# Run gunicorn from the root of the repo
cd /app

# Use full module path
exec gunicorn --bind 0.0.0.0:$PORT league_tracker.app:app -k uvicorn.workers.UvicornWorker