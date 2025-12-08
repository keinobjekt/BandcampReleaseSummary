"""
Session and release metadata persistence utilities.

Stores Gmail-scraped release metadata (not Bandcamp-enriched) keyed by
release date so we can reuse it across runs and avoid re-downloading
messages for dates we've already processed.
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

CacheType = Dict[str, List[dict]]

CACHE_PATH = Path("data") / "release_cache.json"
EMPTY_PATH = Path("data") / "no_results_dates.json"
EMBED_CACHE_PATH = Path("data") / "embed_cache.json"


def _ensure_cache_dir() -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)


def _load_cache() -> CacheType:
    _ensure_cache_dir()
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data  # type: ignore[return-value]
    except Exception:
        # Fall back to empty cache on malformed file
        pass
    return {}


def _save_cache(cache: CacheType) -> None:
    _ensure_cache_dir()
    tmp_path = CACHE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    tmp_path.replace(CACHE_PATH)


def _load_embed_cache() -> Dict[str, dict]:
    _ensure_cache_dir()
    if not EMBED_CACHE_PATH.exists():
        return {}
    try:
        with open(EMBED_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_embed_cache(cache: Dict[str, dict]) -> None:
    _ensure_cache_dir()
    tmp_path = EMBED_CACHE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    tmp_path.replace(EMBED_CACHE_PATH)


def _load_empty_dates() -> Set[datetime.date]:
    _ensure_cache_dir()
    if not EMPTY_PATH.exists():
        return set()
    try:
        with open(EMPTY_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            dates = set()
            for item in raw if isinstance(raw, list) else []:
                day = _to_date(item)
                if day:
                    dates.add(day)
            return dates
    except Exception:
        return set()


def _save_empty_dates(dates: Set[datetime.date]) -> None:
    _ensure_cache_dir()
    tmp_path = EMPTY_PATH.with_suffix(".tmp")
    payload = sorted(day.isoformat() for day in dates)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp_path.replace(EMPTY_PATH)


def _to_date(val) -> datetime.date | None:
    """Normalize string or date into a date object (YYYY-MM-DD or YYYY/MM/DD)."""
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def _dedupe_by_url(items: Iterable[dict]) -> List[dict]:
    seen = set()
    deduped = []
    for item in items:
        url = item.get("url")
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        deduped.append(item)
    return deduped


def persist_release_metadata(releases: Iterable[dict], *, exclude_today: bool = True) -> None:
    """
    Save release metadata into the cache, keyed by release date.
    Skips today's date when exclude_today is True.
    """
    cache = _load_cache()
    empty_dates = _load_empty_dates()
    today = datetime.date.today()
    for release in releases:
        day = _to_date(release.get("date"))
        if not day:
            continue
        if exclude_today and day == today:
            continue
        key = day.isoformat()
        existing = cache.get(key, [])
        # avoid duplicates for the same day by URL
        combined = _dedupe_by_url([*existing, release])
        cache[key] = combined
        # if we now have data for a day that was previously marked empty, clear that marker
        if day in empty_dates:
            empty_dates.discard(day)
    _save_cache(cache)
    _save_empty_dates(empty_dates)


def cached_releases_for_range(start: datetime.date, end: datetime.date) -> Tuple[List[dict], List[datetime.date]]:
    """
    Return (cached_releases, missing_dates) for the inclusive date range.
    missing_dates are days with no cached entries.
    """
    cache = _load_cache()
    empty_dates = _load_empty_dates()
    cursor = start
    cached: List[dict] = []
    missing: List[datetime.date] = []
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        iso = cursor.isoformat()
        releases_for_day = cache.get(iso)
        if releases_for_day:
            cached.extend(releases_for_day)
        elif cursor in empty_dates:
            # known empty date; skip fetching in future sessions
            pass
        else:
            missing.append(cursor)
        cursor += one_day
    return _dedupe_by_url(cached), missing


def collapse_date_ranges(dates: List[datetime.date]) -> List[Tuple[datetime.date, datetime.date]]:
    """Collapse a list of dates into contiguous inclusive ranges."""
    if not dates:
        return []
    dates = sorted(set(dates))
    ranges: List[Tuple[datetime.date, datetime.date]] = []
    start = prev = dates[0]
    for day in dates[1:]:
        if day == prev + datetime.timedelta(days=1):
            prev = day
            continue
        ranges.append((start, prev))
        start = prev = day
    ranges.append((start, prev))
    return ranges


def persist_empty_date_range(start: datetime.date, end: datetime.date, *, exclude_today: bool = True) -> None:
    """
    Record a contiguous date range that returned no Gmail results so we avoid
    querying it again. Optionally excludes today's date.
    """
    if start > end:
        return
    empty_dates = _load_empty_dates()
    today = datetime.date.today()
    cursor = start
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        if not (exclude_today and cursor == today):
            empty_dates.add(cursor)
        cursor += one_day
    _save_empty_dates(empty_dates)


# --------------------------------------------------------------------------- #
# Embed metadata cache (Bandcamp embed info)

def load_embed_cache() -> Dict[str, dict]:
    """Return the cached embed metadata keyed by release URL."""
    return _load_embed_cache()


def persist_embed_metadata(url: str, *, release_id=None, is_track=None, embed_url=None) -> None:
    """
    Save embed metadata for a Bandcamp release URL to avoid refetching later.
    """
    if not url:
        return
    cache = _load_embed_cache()
    existing = cache.get(url, {})
    merged = {
        "release_id": existing.get("release_id"),
        "is_track": existing.get("is_track"),
        "embed_url": existing.get("embed_url"),
    }
    if release_id is not None:
        merged["release_id"] = release_id
    if is_track is not None:
        merged["is_track"] = is_track
    if embed_url is not None:
        merged["embed_url"] = embed_url
    cache[url] = merged
    _save_embed_cache(cache)
    return merged
