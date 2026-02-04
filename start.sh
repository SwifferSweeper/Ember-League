#!/bin/bash

# Install dependencies
cd league_tracker
pip install -r requirements.txt

# Run gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
