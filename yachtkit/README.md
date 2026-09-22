# YachtKit

Free launch-kit generator for yacht brokers. Paste a spec sheet, get a
listing description plus three social posts, formatted and ready to copy.

First kit is free. The second one asks for an email. No accounts, no
friction.

## Run locally

python3 app.py

Then open http://127.0.0.1:8099

## Deploy

The app reads its model key from the `TOGETHER_API_KEY` environment
variable and calls the Together AI API directly over HTTPS. Set `PORT`
and `YACHTKIT_BIND=0.0.0.0` on the host. A `render.yaml` blueprint is
included for one-click deploy on Render; add your `TOGETHER_API_KEY`
in the Render dashboard.

Local dev can fall back to the workspace Together skill CLI when no API
key is set. That path never leaves the dev machine.

## Privacy

Specs are used only to generate the kit. Basic usage logs (IP address,
and email if shared) are kept to prevent abuse. Data is never sold.
