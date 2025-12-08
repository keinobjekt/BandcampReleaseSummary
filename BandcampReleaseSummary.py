import pickle
import argparse
import datetime
from pathlib import Path

from gmail import gmail_authenticate, search_messages, get_messages, scrape_info_from_email
from bandcamp import scrape_info_from_bc_page
from util import construct_release
from generate import generate_html
from dashboard import write_release_dashboard
from session_store import (
    cached_releases_for_range,
    collapse_date_ranges,
    persist_empty_date_range,
    persist_release_metadata,
)

## Settings ##
k_no_download = False
k_data_dir = "data"
k_output_path = "output"
k_embed_proxy_url = "http://localhost:5050/embed-meta"


# ------------------------------------------------------------------------ 
def _parse_date(date_text: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_text, "%Y/%m/%d").date()
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY/MM/DD")


def _daterange(start: datetime.date, end: datetime.date):
    current = start
    one_day = datetime.timedelta(days=1)
    while current <= end:
        yield current
        current += one_day


# ------------------------------------------------------------------------ 
# Fetch releases, combining cached metadata with minimal Gmail downloads
def gather_releases_with_cache(after_date: str, before_date: str, max_results: int, batch_size: int, log=print):
    """
    Use cached Gmail-scraped release metadata for previously seen dates.
    Only hit Gmail for dates in the requested range that have no cache entry.
    """
    start_date = _parse_date(after_date)
    end_date = _parse_date(before_date)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")

    cached_releases, missing_dates = cached_releases_for_range(start_date, end_date)
    missing_ranges = collapse_date_ranges(missing_dates)
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
            log (f'Found {len(message_ids)} messages for {query_after} to {query_before}')
            emails = get_messages(service, [msg["id"] for msg in message_ids], "full", batch_size)
            new_releases = construct_release_list(emails)
            log(f'Parsed {len(new_releases)} releases from Gmail for {query_after} to {query_before}.')
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


# ------------------------------------------------------------------------ 
# Create a list of releases with metadata
def construct_release_list(emails):

    print ('Parsing messages...')
    releases_unsifted = []
    for _, email in emails.items():
        # handle new structure with html + date
        date_header = None
        html_text = email
        if isinstance(email, dict):
            html_text = email.get("html")
            date_header = email.get("date")

        date, img_url, release_url, is_track, artist_name, release_title, page_name = scrape_info_from_email(html_text, date_header)
        
        if not all(x==None for x in [date, img_url, release_url, is_track, artist_name, release_title, page_name]):                
            releases_unsifted.append(construct_release(date=date,
                                                      img_url=img_url,
                                                      release_url=release_url,
                                                      is_track=is_track,
                                                      artist_name=artist_name,
                                                      release_title=release_title,
                                                      page_name=page_name))

    # Sift releases with identical urls
    print(f'Checking for releases with identical URLS...')
    releases = []
    release_urls = []
    for release in releases_unsifted:
        if release['url'] not in release_urls:
            release_urls.append(release['url'])
            releases.append(construct_release(is_track=release['is_track'],
                                              date=release['date'], 
                                              img_url=release['img_url'], 
                                              release_url=release['url'],
                                              artist_name=release.get('artist'),
                                              release_title=release.get('title'),
                                              page_name=release.get('page_name')))

    return releases


# ------------------------------------------------------------------------ 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Gmail for Bandcamp release notifications and generate an HTML file of Bandcamp player widgets.")

    parser.add_argument("-e", "--earliest",     help="Earliest date, YYYY/MM/DD",   default="",             type=str)
    parser.add_argument("-l", "--latest",       help="Latest date, YYYY/MM/DD",     default="today",        type=str)
    parser.add_argument("-m", "--max_results",  help="Maximum results to fetch",    default=2000,           type=int)
    parser.add_argument("-r", "--results_pp",   help="Results per output page",     default=50,             type=int)
    parser.add_argument("-b", "--batch-size",   help="Gmail API batch size",        default=20,             type=int)

    args = parser.parse_args()

    max_results = args.max_results
    after_date  = args.earliest
    before_date = args.latest if args.latest != "today" else f'{datetime.date.today().year}/{datetime.date.today().month:02d}/{datetime.date.today().day:02d}'
    results_pp  = args.results_pp
    batch_size  = args.batch_size

    # Validate args
    def validate(date_text):
        date = _parse_date(date_text)
        if date.year < 2000 or date.year > datetime.datetime.now().year:
            raise ValueError("Year must be between 2000 and today")    

    validate(after_date)
    validate(before_date)

    # Create output directory
    output_dir_name = f'{k_output_path}/bandcamp_listings_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}'
    Path(k_data_dir).mkdir(exist_ok=True)
    Path(output_dir_name).mkdir(exist_ok=True)

    # Fetch releases with cache awareness
    releases = gather_releases_with_cache(after_date, before_date, max_results, batch_size)
    
    # Generate HTML pages
    write_release_dashboard(releases=releases, 
                            output_path=f"{output_dir_name}/output.html",
                            title="Bandcamp Release Dashboard",
                            fetch_missing_ids=False,
                            embed_proxy_url=k_embed_proxy_url)
    
    print(f"Dashboard written to {output_dir_name}/output.html")
    
    #generate_html(releases, output_dir_name, results_pp)
