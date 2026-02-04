#!/bin/bash

# Change to the app directory using absolute path
cd /app/league_tracker

# Run gunicorn from the league_tracker directory
exec gunicorn --bind 0.0.0.0:$PORT app:app
