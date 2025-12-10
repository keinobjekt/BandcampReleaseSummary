def construct_release(is_track=None, release_url=None, date=None, img_url=None, artist_name=None, release_title=None, page_name=None, release_id=None):
    release = {}
    release['img_url'] = img_url
    release['date'] = date
    release['artist'] = artist_name
    release['title'] = release_title
    release['page_name'] = page_name
    release['url'] = release_url
    release['release_id'] = release_id
    release['is_track'] = is_track
    return release


def get_data_dir():
    """
    Return a writable data directory for caches/settings.
    On macOS, prefer ~/Library/Application Support/bcfeed.
    Otherwise, fall back to a hidden folder in the user's home.
    """
    from pathlib import Path
    home = Path.home()
    app_support = home / "Library" / "Application Support" / "bcfeed"
    if app_support.parent.exists():  # likely macOS
        base = app_support
    else:
        base = home / ".bcfeed"
    base.mkdir(parents=True, exist_ok=True)
    return base

        
