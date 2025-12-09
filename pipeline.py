import datetime
from typing import Dict, Iterable, Tuple

from gmail import gmail_authenticate, search_messages, get_messages, scrape_info_from_email
from util import construct_release
from session_store import (
    cached_releases_for_range,
    collapse_date_ranges,
    persist_empty_date_range,
    persist_release_metadata,
)


def parse_date(date_text: str) -> datetime.date:
    """Parse a YYYY/MM/DD string into a date, raising on failure."""
    try:
        return datetime.datetime.strptime(date_text, "%Y/%m/%d").date()
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY/MM/DD")


def construct_release_list(emails: Dict) -> list[dict]:
    """Parse Gmail messages into release dicts."""
    print("Parsing messages...")
    releases_unsifted = []
    for _, email in emails.items():
        date_header = None
        html_text = email
        if isinstance(email, dict):
            html_text = email.get("html")
            date_header = email.get("date")

        date, img_url, release_url, is_track, artist_name, release_title, page_name = scrape_info_from_email(
            html_text, date_header, email.get("subject")
        )

        if not all(x is None for x in [date, img_url, release_url, is_track, artist_name, release_title, page_name]):
            releases_unsifted.append(
                construct_release(
                    date=date,
                    img_url=img_url,
                    release_url=release_url,
                    is_track=is_track,
                    artist_name=artist_name,
                    release_title=release_title,
                    page_name=page_name,
                )
            )

    # Sift releases with identical urls
    print("Checking for releases with identical URLS...")
    releases = []
    release_urls = []
    for release in releases_unsifted:
        if release["url"] not in release_urls:
            release_urls.append(release["url"])
            releases.append(
                construct_release(
                    is_track=release["is_track"],
                    date=release["date"],
                    img_url=release["img_url"],
                    release_url=release["url"],
                    artist_name=release.get("artist"),
                    release_title=release.get("title"),
                    page_name=release.get("page_name"),
                )
            )

    return releases


def gather_releases_with_cache(after_date: str, before_date: str, max_results: int, batch_size: int, log=print):
    """
    Use cached Gmail-scraped release metadata for previously seen dates.
    Only hit Gmail for dates in the requested range that have no cache entry.
    """
    start_date = parse_date(after_date)
    end_date = parse_date(before_date)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")

    cached_releases, missing_dates = cached_releases_for_range(start_date, end_date)
    missing_ranges: Iterable[Tuple[datetime.date, datetime.date]] = collapse_date_ranges(missing_dates)
    releases = list(cached_releases)

    if missing_ranges:
        log(f"Cached releases are available for {len(releases)} entries; {len(missing_ranges)} missing date span(s) will be fetched from Gmail.")
        log("")
        log("The following date ranges will be downloaded from Gmail:")
        for start_missing, end_missing in missing_ranges:
            log(f"  {start_missing} to {end_missing}")
    else:
        log(f"Cached releases are available for {len(releases)} entries; no Gmail download needed for this range.")

    cap_reached = False
    remaining = max_results - len(releases)
    if remaining <= 0:
        # Respect the user's cap: do not download more if cache already exceeds limit
        log(f"Maximum results of {max_results} already satisfied by cache; no Gmail download needed.")
        cap_reached = True
    else:
        service = gmail_authenticate()

        for start_missing, end_missing in missing_ranges:
            if remaining <= 0:
                log(f"Reached maximum results of {max_results}; stopping further Gmail downloads.")
                break
            query_after = start_missing.strftime("%Y/%m/%d")
            query_before = end_missing.strftime("%Y/%m/%d")
            search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{query_before} after:{query_after}"
            log("")
            log(f"Querying Gmail for {query_after} to {query_before} (remaining cap {remaining})")
            message_ids = search_messages(service, search_query, max_results=remaining)
            if not message_ids:
                log(f"No messages found for {query_after} to {query_before}")
                persist_empty_date_range(start_missing, end_missing, exclude_today=True)
                continue
            log(f"Found {len(message_ids)} messages for {query_after} to {query_before}")
            emails = get_messages(service, [msg["id"] for msg in message_ids], "full", batch_size)
            new_releases = construct_release_list(emails)
            log(f"Parsed {len(new_releases)} releases from Gmail for {query_after} to {query_before}.")
            releases.extend(new_releases)
            persist_release_metadata(new_releases, exclude_today=True)
            remaining = max_results - len(releases)

    # Deduplicate on URL after combining cached + new
    seen_urls = set()
    deduped = []
    for release in releases:
        url = release.get("url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(release)

    log("")
    if cap_reached:
        log(f"Final total of {len(deduped)} unique releases (capped at {max_results} from cache).")
    else:
        log(f"Total of {len(deduped)} unique releases after combining cache and Gmail downloads.")

    # Always persist the run results when a page will be generated, so cache is up to date.
    persist_release_metadata(deduped, exclude_today=True)

    return deduped[:max_results] if max_results else deduped
