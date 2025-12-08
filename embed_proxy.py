"""
Simple proxy to fetch Bandcamp release metadata and embed URLs to avoid CORS in the browser.

Run locally:
    python embed_proxy.py

Then configure the dashboard to use the proxy, e.g. embed_proxy_url="http://localhost:5000/embed-meta".
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

app = Flask(__name__)

def _load_viewed() -> set[str]:
    if not VIEWED_PATH.exists():
        return set()
    try:
        data = json.loads(VIEWED_PATH.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def _save_viewed(items: set[str]) -> None:
    tmp = VIEWED_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(items)), encoding="utf-8")
    tmp.replace(VIEWED_PATH)


def _corsify(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
VIEWED_PATH = DATA_DIR / "viewed_state.json"
RELEASE_CACHE_PATH = DATA_DIR / "release_cache.json"
EMPTY_DATES_PATH = DATA_DIR / "no_results_dates.json"
EMBED_CACHE_PATH = DATA_DIR / "embed_cache.json"


def extract_bc_meta(html_text: str) -> Optional[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
    meta = soup.find("meta", attrs={"name": "bc-page-properties"})
    if not meta or "content" not in meta.attrs:
        return None
    raw = meta["content"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return ast.literal_eval(raw)


def build_embed_url(item_id: Optional[int], is_track: bool) -> Optional[str]:
    if not item_id:
        return None
    kind = "track" if is_track else "album"
    base = "https://bandcamp.com/EmbeddedPlayer"
    return f"{base}/{kind}={item_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/"


@app.route("/viewed-state", methods=["GET", "POST", "OPTIONS"])
def viewed_state():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    if request.method == "GET":
        items = sorted(_load_viewed())
        return _corsify(jsonify({"viewed": items}))

    data = request.get_json(silent=True) or {}
    url = data.get("url")
    read = data.get("read")
    if not url or not isinstance(read, bool):
        return _corsify(jsonify({"error": "Missing url or read flag"})), 400
    items = _load_viewed()
    if read:
        items.add(url)
    else:
        items.discard(url)
    _save_viewed(items)
    return _corsify(jsonify({"ok": True}))


@app.route("/embed-meta", methods=["GET", "OPTIONS"])
def embed_meta():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    release_url = request.args.get("url")
    if not release_url:
        return _corsify(jsonify({"error": "Missing url parameter"})), 400
    try:
        resp = requests.get(
            release_url,
            headers={"User-Agent": "BandcampReleaseDashboard/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        return _corsify(jsonify({"error": f"Failed to fetch Bandcamp page: {exc}"})), 502

    data = extract_bc_meta(resp.text)
    if not data:
        return _corsify(jsonify({"error": "Unable to find bc-page-properties meta"})), 404

    item_id = data.get("item_id")
    is_track = data.get("item_type") == "track"
    embed_url = build_embed_url(item_id, is_track)

    response = jsonify(
        {"release_id": item_id, "is_track": is_track, "embed_url": embed_url}
    )
    return _corsify(response)


@app.route("/reset-caches", methods=["POST", "OPTIONS"])
def reset_caches():
    if request.method == "OPTIONS":
        return _corsify(app.response_class(status=204))
    data = request.get_json(silent=True) or {}
    clear_cache = bool(data.get("clear_cache", False))
    clear_viewed = bool(data.get("clear_viewed", False))

    cleared = []
    errors = []

    def _safe_unlink(path: Path):
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        return False

    if clear_cache:
        for p in (RELEASE_CACHE_PATH, EMPTY_DATES_PATH, EMBED_CACHE_PATH):
            if _safe_unlink(p):
                cleared.append(p.name)
    if clear_viewed:
        if _safe_unlink(VIEWED_PATH):
            cleared.append(VIEWED_PATH.name)

    return _corsify(jsonify({"ok": True, "cleared": cleared, "errors": errors}))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
