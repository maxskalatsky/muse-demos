#!/usr/bin/env bash
# Start the YachtKit wedge server locally.
# Usage: ./run.sh   -> serves on http://127.0.0.1:8099
# The server runs in the background; logs go to server.log.
set -e
cd "$(dirname "$0")"
if curl -s -o /dev/null -m 2 http://127.0.0.1:8099/; then
  echo "YachtKit already running on http://127.0.0.1:8099"
  exit 0
fi
nohup python3 app.py > server.log 2>&1 &
sleep 2
curl -s -o /dev/null http://127.0.0.1:8099/ && echo "YachtKit running on http://127.0.0.1:8099"
