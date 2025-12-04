import pickle
import argparse
import datetime
from pathlib import Path

from gmail import gmail_authenticate, search_messages, get_messages, scrape_info_from_email
from bandcamp import scrape_info_from_bc_page

## Settings ##
k_no_download = False
k_data_dir = "data"
k_output_path = "output"


# ------------------------------------------------------------------------ 
# UTIL
# ------------------------------------------------------------------------ 
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

        
# ------------------------------------------------------------------------ 
def get_widget_string(release_id, release_url, is_track):
    if is_track:
        return f'<iframe style="border: 0; width: 400px; height: 120px;" src="https://bandcamp.com/EmbeddedPlayer/track={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=false/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'
    else:
        return f'<iframe style="border: 0; width: 400px; height: 274px;" src="https://bandcamp.com/EmbeddedPlayer/album={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'




# ------------------------------------------------------------------------ 
# Create a list of releases with metadata
def construct_release_list(raw_emails):

    print ('Parsing messages...')
    releases_unsifted = []
    for _, email in raw_emails.items():
        date, img_url, release_url, is_track = scrape_info_from_email(email)
        
        if not all(x==None for x in [date, img_url, release_url, is_track]):                
            releases_unsifted.append(construct_release(date=date, img_url=img_url, release_url=release_url, is_track=is_track))

    # Sift releases with identical urls
    print ('Discarding releases with identical URLS...')
    releases = []
    release_urls = []
    for release in releases_unsifted:
        if release['url'] not in release_urls:
            release_urls.append(release['url'])
            releases.append(construct_release(is_track=release['is_track'],
                                                date=release['date'], 
                                                img_url=release['img_url'], 
                                                release_url=release['url']))
    print (f'Removed duplicated releases - originally {len(releases_unsifted)}, now {len(releases)}')

    # Scrape the rest of the info from bandcamp page
    for release in releases:
        release = scrape_info_from_bc_page (release)

    return releases


# ------------------------------------------------------------------------ 
def generate_html(releases, output_dir_name, results_pp):

    print('Generating HTML...')
    odd_num_releases = len(releases) % 2 != 0
    if odd_num_releases: # append blank release to ensure releases list has an even number
        releases.append(construct_release())

    page = 1

    from math import ceil
    num_pages = int(ceil(len(releases) / results_pp))
    
    while len(releases):

        releases_this_page = releases[0:results_pp]
        it = iter(releases_this_page)

        doc = '<html>'
        doc += '<body>'

        def get_bc_page_url(url, is_track):
            # we can't just search for ".com" here because the url is sometimes
            # a custom label domain
            page_url = None
            if url is not None:
                if is_track:
                    page_url = url.rsplit("/track/")[0]
                else:
                    page_url = url.rsplit("/album/")[0]
            return page_url

        for release1 in it:
            release2 = next(it)
            page_url_1 = get_bc_page_url(release1['url'], release1['is_track'])
            page_url_2 = get_bc_page_url(release2['url'], release2['is_track'])
            widget_string_1 = get_widget_string(release1['release_id'], release1['url'], release1['is_track'])
            widget_string_2 = get_widget_string(release2['release_id'], release2['url'], release2['is_track'])
            doc += '<p>'
            doc += '<table>'
            doc += f'<b><tr><th>{release1["date"]} / {release1["page_name"]}</th> <th>{release2["date"]} / {release2["page_name"]}</th></tr></b>'
            doc += f'<tr><td align="center"><i><a href="{release1["url"]}">{page_url_1}</a></i></td> <td align="center"><i><a href="{release2["url"]}">{page_url_2}</a></i></td></tr>'
            doc += f'<tr><td>{widget_string_1}</td><td>{widget_string_2}</td></tr>'
            doc += '</table>'
            doc += '</p>'

        doc += '<p>'

        page_links = ''

        if page > 1:
            page_links += f'<a href=page_{page-1}.html><</a> '
        
        for p in range(1, page):
            page_links += f'<a href=page_{p}.html>{p}</a> '
        page_links += f'<b>{page} </b> '
        for p in range(page+1, num_pages+1):
            page_links += f'<a href=page_{p}.html>{p}</a> '
        
        if page < num_pages:
            page_links += f'<a href=page_{page+1}.html>></a>'

        doc += page_links
        doc += '</p>'
        doc += '</body>'
        doc += '</html>'

        with open(f'{output_dir_name}/page_{page}.html', 'w') as file:
            file.write(doc)

        releases = releases[results_pp:]

        page += 1
        print(f'Writing {output_dir_name}/page_{page}.html...')

    print('HTML generated!')


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
        try:
            date = datetime.datetime.strptime(date_text, '%Y/%m/%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY/MM/DD")
        if date.year < 2000 or date.year > datetime.datetime.now().year:
            raise ValueError("Year must be between 2000 and today")    

    validate(after_date)
    validate(before_date)

    # Create output directory
    output_dir_name = f'{k_output_path}/bandcamp_listings_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}'
    Path(k_data_dir).mkdir(exist_ok=True)
    Path(output_dir_name).mkdir(exist_ok=True)

    # get the Gmail API service
    service = gmail_authenticate()

    # Search inbox
    search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{before_date} after:{after_date}"
    message_ids = search_messages(service, search_query, max_results=max_results)
    
    # Get messages    
    email_data_file = f'email_data_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}.pkl'
    if k_no_download:
        with open(f"{k_data_dir}/{email_data_file}", "rb") as a_file:
            raw_emails = pickle.load(a_file)
    else:
        raw_emails = get_messages(service, [msg['id'] for msg in message_ids], 'raw', batch_size)
        with open(f"{k_data_dir}/{email_data_file}", "wb+") as a_file:
            pickle.dump(raw_emails, a_file)
    
    # Compile list of releases
    release_info_file = f'release_data_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}.pkl'
    if k_no_download:
        print ('Opening saved release list...')
        with open(f"{k_data_dir}/{release_info_file}", "rb") as a_file:
            releases = pickle.load(a_file)
    else:
        releases = construct_release_list(raw_emails)
        with open(f"{k_data_dir}/{release_info_file}", "wb+") as a_file:
            pickle.dump(releases, a_file)
    
    generate_html(releases, output_dir_name, results_pp)
