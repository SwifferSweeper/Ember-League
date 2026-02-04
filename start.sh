#!/bin/bash

# Change to the app directory where app.py is located
cd "$(dirname "$0")/league_tracker"

# Run gunicorn from the league_tracker directory
exec gunicorn --bind 0.0.0.0:$PORT app:app
