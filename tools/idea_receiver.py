#!/usr/bin/env python3
"""Stage-1 stand-in for the form service: receives the "Help develop Boombaland" form on 127.0.0.1:8767 and stores each
submission as one JSON file in local/ideas/ (git-ignored). Only for this machine; never deployed.

Run:  python3 -I tools/idea_receiver.py      (from the repo root, as a background task)
"""
import datetime
import json
import os
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "local", "ideas")
ALLOWED = {"http://127.0.0.1:8766", "http://localhost:8766"}
LIMITS = {"title": 120, "idea": 5000, "name": 80, "email": 200}


class H(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/submit":
            return self._reply(404, {"success": False, "message": "not found"})
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n > 20000:
            return self._reply(413, {"success": False, "message": "too large"})
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._reply(400, {"success": False, "message": "bad json"})
        if data.get("botcheck"):
            return self._reply(200, {"success": True})  # honeypot filled: drop silently
        rec = {k: str(data.get(k, "")).strip()[:lim] for k, lim in LIMITS.items()}
        if not rec["title"] or not rec["idea"]:
            return self._reply(400, {"success": False, "message": "title and idea are required"})
        if data.get("consent") != "yes":
            return self._reply(400, {"success": False, "message": "consent is required"})
        if (rec["name"] or rec["email"]) and data.get("age16") != "yes":
            return self._reply(400, {"success": False, "message": "contact details need the 16+ box"})
        if rec["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", rec["email"]):
            return self._reply(400, {"success": False, "message": "bad email"})
        rec.update(age16=data.get("age16") == "yes", consent=True,
                   received=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
        os.makedirs(OUT, exist_ok=True)
        name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3) + ".json"
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        print("stored", name, flush=True)
        return self._reply(200, {"success": True})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("idea receiver on http://127.0.0.1:8767/submit ->", OUT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8767), H).serve_forever()
