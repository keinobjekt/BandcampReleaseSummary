"""
Generate an interactive Bandcamp release dashboard from scraped Gmail data.

Usage
-----
Call ``build_release_dashboard_html`` with a list of release dictionaries that
look like::

    {
        "artist": "Artist Name",
        "release_name": "Album or Track Title",
        "page_name": "label-or-page-name",
        "date": "2024-12-31",
        "URL": "https://example.bandcamp.com/album/example-release"
    }

Optionally provide ``release_id`` and ``is_track`` if you have them already to
avoid an extra scrape per release. The function returns a string of HTML you
can write to disk. ``write_release_dashboard`` is a small helper that writes
the file for you.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from dashboard_html import render_dashboard_html
from session_store import load_embed_cache, persist_embed_metadata


# --------------------------------------------------------------------------- #
# Bandcamp helpers

def _guess_is_track(release_url: str) -> bool:
    """Heuristic for determining whether a release URL points to a track."""
    return "/track/" in (release_url or "")


def _build_embed_url(release_id: Optional[int], release_url: str, is_track: bool) -> Optional[str]:
    """
    Compose the Bandcamp embed URL if we have enough info, otherwise None.
    """
    if not release_id:
        return None
    kind = "track" if is_track else "album"
    base = "https://bandcamp.com/EmbeddedPlayer"
    return f"{base}/{kind}={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/"


def fetch_embed_metadata(release_url: str, timeout: int = 10) -> Dict[str, Optional[str]]:
    """
    Scrape a Bandcamp release page to pull out the numeric ID and type so we can
    build an embed URL.
    """
    result = {"release_id": None, "is_track": _guess_is_track(release_url)}
    if not release_url:
        return result

    try:
        req = Request(release_url, headers={"User-Agent": "BandcampReleaseDashboard/1.0"})
        html_text = urlopen(req, timeout=timeout).read().decode("utf-8", errors="replace")
    except URLError as exc:
        print(f"Warning: unable to fetch Bandcamp page at {release_url}: {exc}")
        return result

    soup = BeautifulSoup(html_text, "html.parser")
    meta_tag = soup.find("meta", attrs={"name": "bc-page-properties"})
    if not meta_tag or "content" not in meta_tag.attrs:
        return result

    raw_content = meta_tag["content"]
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        data = ast.literal_eval(raw_content)

    release_id = data.get("item_id")
    item_type = data.get("item_type", "")

    result["release_id"] = release_id
    result["is_track"] = item_type == "track" if item_type else result["is_track"]
    return result


EMBED_CACHE = load_embed_cache()


# --------------------------------------------------------------------------- #
# HTML generation

def _normalize_release(
    entry: Dict[str, str],
    fetch_missing_ids: bool,
    log: Callable[[str], None] | None = None,
    progress_index: int | None = None,
    progress_total: int | None = None,
) -> Dict[str, str]:
    """
    Map incoming data keys onto a consistent shape used by the dashboard.
    """
    url = entry.get("URL") or entry.get("url") or ""
    release_id = entry.get("release_id")
    is_track = entry.get("is_track")
    embed_url = entry.get("embed_url")
    fetched_meta = False

    cached_meta = EMBED_CACHE.get(url) if url else None
    if cached_meta:
        if release_id is None:
            release_id = cached_meta.get("release_id")
        if is_track is None:
            is_track = cached_meta.get("is_track")
        if embed_url is None:
            embed_url = cached_meta.get("embed_url")

    if release_id is None and fetch_missing_ids:
        if log:
            if progress_index and progress_total:
                log(f"({progress_index}/{progress_total}) {url}")
            else:
                log(f"Fetching Bandcamp page for {url}")
        meta = fetch_embed_metadata(url)
        release_id = meta["release_id"]
        is_track = meta["is_track"]
        fetched_meta = True

    if is_track is None:
        is_track = _guess_is_track(url)

    # Only pre-build an embed URL when we already have the ID; otherwise we will
    # fetch lazily in the browser when a row is expanded.
    embed_url = embed_url or (_build_embed_url(release_id, url, is_track) if release_id else None)

    if fetched_meta and url:
        merged = persist_embed_metadata(
            url,
            release_id=release_id,
            is_track=is_track,
            embed_url=embed_url,
        )
        if merged:
            EMBED_CACHE[url] = merged

    return {
        "artist": entry.get("artist") or "",
        "title": entry.get("release_name") or entry.get("title") or "",
        "page_name": entry.get("page_name") or "",
        "date": entry.get("date") or "",
        "url": url,
        "release_id": release_id,
        "is_track": is_track,
        "embed_url": embed_url,
    }


def build_release_dashboard_html(
    releases: Iterable[Dict[str, str]],
    *,
    title: str = "Bandcamp Release Dashboard",
    fetch_missing_ids: bool = False,
    log: Callable[[str], None] | None = None,
    embed_proxy_url: str | None = None,
    default_theme: str | None = None,
) -> str:
    """Return a full HTML document for browsing Bandcamp releases."""
    # Reload embed cache each build so embeds fetched in prior sessions (e.g., via
    # browser expansion hitting the proxy) are reflected in the badges/URLs.
    EMBED_CACHE.clear()
    EMBED_CACHE.update(load_embed_cache())
    releases_list = list(releases)
    total = len(releases_list)
    log(f'Prefetching Bandcamp players not already in cache...')
    normalized: List[Dict[str, str]] = [
        _normalize_release(entry, fetch_missing_ids, log, idx, total)
        for idx, entry in enumerate(releases_list, start=1)
    ]
    data_json = json.dumps(normalized, ensure_ascii=True)
    return render_dashboard_html(title=title, data_json=data_json, embed_proxy_url=embed_proxy_url, default_theme=default_theme)


def write_release_dashboard(
    releases: Iterable[Dict[str, str]],
    output_path: str | Path,
    *,
    title: str = "Bandcamp Release Dashboard",
    fetch_missing_ids: bool = False,
    log: Callable[[str], None] | None = None,
    embed_proxy_url: str | None = None,
    default_theme: str | None = None,
) -> Path:
    """
    Convenience helper that writes the dashboard HTML to disk.
    """
    output_path = Path(output_path)
    html_doc = build_release_dashboard_html(
        releases,
        title=title,
        fetch_missing_ids=fetch_missing_ids,
        embed_proxy_url=embed_proxy_url,
        log=log,
        default_theme=default_theme,
    )
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    # Example usage
    sample_releases = [
        {
            "artist": "DJ JM",
            "release_name": "Barrakuda EP",
            "page_name": "DJ JM",
            "date": "2024-12-31",
            "URL": "https://djjm1.bandcamp.com/album/barrakuda-ep"
        },
        {
            "artist": "Tarker",
            "release_name": "Fading Realities EP",
            "page_name": "Mord",
            "date": "2024-11-15",
            "URL": "https://mord.bandcamp.com/album/fading-realities-ep"
        }
    ]
    output_file = write_release_dashboard(
        sample_releases,
        output_path="bandcamp_release_dashboard.html",
        title="My Bandcamp Releases",
        fetch_missing_ids=True
    )
    print(f"Dashboard written to {output_file}")
