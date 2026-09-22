#!/usr/bin/env python3
"""YachtKit wedge: free launch-kit generator for yacht brokers.

Single-file stdlib server. Serves the static page and exposes
POST /api/generate, which calls Together AI server-side.
Emails are captured to emails.jsonl. No analytics, no external assets.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
EMAIL_LOG = os.path.join(HERE, "emails.jsonl")
TOGETHER_CLI = "/home/hatch/workspace/skills/together-ai/bin/together.py"
MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

PORT = int(os.environ.get("PORT", os.environ.get("YACHTKIT_PORT", "8099")))
BIND = os.environ.get("YACHTKIT_BIND", "127.0.0.1")
RATE_LIMIT = 5          # max generations
RATE_WINDOW = 3600      # per hour, per client IP

_hits: dict[str, list[float]] = {}

SYSTEM_PROMPT = (
    "You are YachtKit, a copywriter for yacht brokers. Write in a plain, "
    "professional broker voice: confident, specific, factual. No hype, no "
    "exclamation marks, no superlatives you cannot support from the input. "
    "Never open with 'This stunning vessel' or any equivalent boilerplate. "
    "Vary sentence structure; anchor every claim in the input specs. "
    "The copy must pass one test: it would not embarrass the broker in front "
    "of a buyer considering a seven-figure purchase. "
    "Never use em dashes; use commas or periods instead. Never invent "
    "specifications (engines, hours, dimensions, equipment). If a detail is "
    "missing from the input, write around it without guessing. Return ONLY "
    "valid JSON, no markdown fences, with exactly these keys: "
    "description (string, 200-350 words of listing copy), "
    "social_posts (array of exactly 3 posts, each 2 to 3 sentences and under "
    "280 characters, plain text, max 3 hashtags each, each post highlights a "
    "different angle: performance, lifestyle, and value/condition)."
)

USER_TEMPLATE = (
    "Generate listing copy for this yacht. Input follows.\n\n"
    "{specs}\n\n"
    "Return only the JSON object described in the system prompt."
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FIRST_KIT_FILE = os.path.join(HERE, "first_kit.json")


def _load_first_kit() -> set:
    try:
        with open(FIRST_KIT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_first_kit(seen: set) -> None:
    try:
        with open(FIRST_KIT_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(seen), f)
    except Exception:
        pass


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    for header in ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP"):
        value = handler.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return handler.client_address[0]


def rate_ok(ip: str) -> bool:
    now = time.time()
    stamps = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
    if len(stamps) >= RATE_LIMIT:
        _hits[ip] = stamps
        return False
    stamps.append(now)
    _hits[ip] = stamps
    return True


def fetch_url_text(url: str) -> tuple[str, bool]:
    """Best-effort fetch of a listing page. Never raises."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "", False
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "12", "-A",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/120.0 Safari/537.36", url],
            capture_output=True, text=True, timeout=20,
        )
        html = r.stdout or ""
        if len(html) < 500:
            return "", False
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000], True
    except Exception:
        return "", False


def call_model(specs: str) -> dict:
    payload = {
        "model": MODEL,
        "temperature": 0.7,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(specs=specs[:6000])},
        ],
    }
    api_key = os.environ.get("TOGETHER_API_KEY", "")
    if api_key:
        # Production path: direct HTTPS call to Together AI.
        import urllib.request
        req = urllib.request.Request(
            "https://api.together.xyz/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json",
                     "User-Agent": "YachtKit/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
    elif os.path.exists(TOGETHER_CLI):
        # Local dev path: workspace skill CLI (never deployed).
        r = subprocess.run(
            [sys.executable, TOGETHER_CLI, "POST", "/v1/chat/completions",
             json.dumps(payload)],
            capture_output=True, text=True, timeout=180,
        )
        data = json.loads(r.stdout)
    else:
        raise RuntimeError("no model backend configured")
    content = data["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            return json.loads(content[start:end + 1])
        return {"description": content, "social_posts": []}


def log_email(email: str, url: str, specs_len: int, ip: str) -> None:
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    entry = {"ts": int(time.time()), "email": email,
             "url": url[:200], "specs_len": specs_len, "ip_hash": ip_hash}
    with open(EMAIL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "YachtKit/1.0"

    def log_message(self, *args):  # keep logs quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            target = os.path.join(STATIC_DIR, "index.html")
        else:
            self._send(404, b"not found", "text/plain")
            return
        try:
            with open(target, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        except FileNotFoundError:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/interest":
            self._handle_interest()
            return
        if path != "/api/generate":
            self._send(404, b"not found", "text/plain")
            return
        ip = client_ip(self)
        if not rate_ok(ip):
            self._send(429, b'{"error":"rate_limited"}',
                       "application/json")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, b'{"error":"bad_request"}', "application/json")
            return

        email = str(body.get("email", "")).strip().lower()
        url = str(body.get("url", "")).strip()
        specs = str(body.get("specs", "")).strip()

        seen = _load_first_kit()
        has_free_kit = ip in seen
        if has_free_kit and not EMAIL_RE.match(email):
            # First kit was free. The second one needs an email.
            self._send(402, b'{"error":"email_required"}', "application/json")
            return

        fetched, fetched_ok = "", False
        if url:
            fetched, fetched_ok = fetch_url_text(url)
        combined = (fetched + "\n\n" + specs).strip()
        if len(combined) < 40:
            self._send(400,
                       b'{"error":"paste spec text (a listing URL alone rarely works)"}',
                       "application/json")
            return

        if EMAIL_RE.match(email):
            log_email(email, url, len(specs), ip)
        if not has_free_kit:
            seen.add(ip)
            _save_first_kit(seen)
        try:
            kit = call_model(combined)
        except Exception as exc:
            self._send(502,
                       json.dumps({"error": "generation failed",
                                   "detail": str(exc)[:200]}).encode(),
                       "application/json")
            return
        kit["url_read_ok"] = fetched_ok
        kit["free_kit_used"] = has_free_kit
        self._send(200, json.dumps(kit).encode(), "application/json")

    def _handle_interest(self):
        """Pro interest capture: just an email, nothing else."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, b'{"error":"bad_request"}', "application/json")
            return
        email = str(body.get("email", "")).strip().lower()
        if not EMAIL_RE.match(email):
            self._send(400, b'{"error":"valid email required"}',
                       "application/json")
            return
        ip = client_ip(self)
        log_email("pro:" + email, "", 0, ip)
        self._send(200, b'{"ok":true}', "application/json")


if __name__ == "__main__":
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    print(f"YachtKit serving on {BIND}:{PORT}", flush=True)
    server.serve_forever()
