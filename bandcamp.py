from bs4 import BeautifulSoup

# Scrape metadata from the Bandcamp page of one release
def scrape_info_from_bc_page(release):
    release_url = release['url']

    k_num_attempts = 5
    for _ in range(k_num_attempts):
        try:
            from urllib.request import Request, urlopen
            req = Request(release_url, headers={'User-Agent': 'XYZ/3.0'})
            html_text = urlopen(req, timeout=10).read().decode()
        except Exception as e:
            html_text = ""
            print(f'Error: Exception while fetching Bandcamp page at {release_url}: {e}')
            return release
        if html_text != "":
            break
        else:
            import time
            time.sleep(5)

    if html_text == "":
        print(f'Error: Could not load bandcamp page at {release_url}: {e}')
        return release

    soup = BeautifulSoup(html_text, 'html.parser')

    # check for bandcamp 404 page
    if "Sorry, that something isn’t here" in html_text:
        print(f'Error: Bandcamp 404 page found at {release_url}')
        return release

    # release title
    release['release_title'] = soup.find('h2', class_="trackTitle")
    if release['release_title'] is not None:
        release['release_title'] = soup.find('h2', class_="trackTitle").text.strip()        
    else:
        print(f'Error: Release title not found while scraping {release_url}')
        return release

    # artist name
    def parse_artist_name(input):
        input = input.strip()
        if (input[0:2] != 'by'):
            return None
        input = input [2:]
        return input.strip()

    release['artist_name'] = soup.find('h3')

    if release['artist_name'] is not None:
        release['artist_name'] = parse_artist_name(soup.find('h3').text)
        if release['artist_name'] == None:
            print(f'Error parsing artist name at {release_url}')
            return release
    else:
        print(f'Artist name not found at {release_url}')
        return release

    # page name 
    release['page_name'] = soup.findAll('span', class_="title")
    if release['page_name'] is not None:
        release['page_name'] = release['page_name'][1].text.strip()
    else:
        print(f'Page name not found at {release_url}')
        return release

    # release id
    release['release_id'] = soup.find('meta', attrs={'name':'bc-page-properties'})
    if release['release_id'] is not None:
        release['release_id'] = eval(release['release_id']["content"])['item_id']
    else:
        print (f'Release ID not found at {release_url}')
        return release

    print(f"Retrieved release data for {release['release_title']} by {release['artist_name']}")

    return release