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
from typing import Dict, Iterable, List, Tuple

CacheType = Dict[str, List[dict]]

CACHE_PATH = Path("data") / "release_cache.json"


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
    _save_cache(cache)


def cached_releases_for_range(start: datetime.date, end: datetime.date) -> Tuple[List[dict], List[datetime.date]]:
    """
    Return (cached_releases, missing_dates) for the inclusive date range.
    missing_dates are days with no cached entries.
    """
    cache = _load_cache()
    cursor = start
    cached: List[dict] = []
    missing: List[datetime.date] = []
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        iso = cursor.isoformat()
        releases_for_day = cache.get(iso)
        if releases_for_day:
            cached.extend(releases_for_day)
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
