#!/bin/bash

# Start Xvfb silently
Xvfb :99 -screen 0 1920x1080x16 > /dev/null 2>&1 &
export DISPLAY=:99

# Start window manager silently
fluxbox > /dev/null 2>&1 &

# Start VNC server silently
x11vnc -display :99 -forever -nopw > /dev/null 2>&1 &

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for web service to initialize database
sleep 5

# Run the scraper with unbuffered output
cd /app
exec python -u -m scraper.scraper 