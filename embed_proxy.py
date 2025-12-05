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
from typing import Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

app = Flask(__name__)


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


@app.route("/embed-meta")
def embed_meta():
    release_url = request.args.get("url")
    if not release_url:
        return jsonify({"error": "Missing url parameter"}), 400
    try:
        resp = requests.get(
            release_url,
            headers={"User-Agent": "BandcampReleaseDashboard/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch Bandcamp page: {exc}"}), 502

    data = extract_bc_meta(resp.text)
    if not data:
        return jsonify({"error": "Unable to find bc-page-properties meta"}), 404

    item_id = data.get("item_id")
    is_track = data.get("item_type") == "track"
    embed_url = build_embed_url(item_id, is_track)

    response = jsonify(
        {"release_id": item_id, "is_track": is_track, "embed_url": embed_url}
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
