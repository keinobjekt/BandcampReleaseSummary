import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
import requests
from bs4 import BeautifulSoup
import json
import argparse
import datetime
from pathlib import Path


## Debug settings ##
use_cached_data = False


# ------------------------------------------------------------------------ UTIL 

def parse_release_url(message_text):
    release_url = None
    search_string = 'a href="https://'
    start_idx = message_text.find(search_string)
    if start_idx >= 0:
        url_start_idx = message_text.find(search_string) + 8
        url_end_idx = message_text.find('"', url_start_idx)
        url_qmark_idx = message_text.find('?', url_start_idx)
        if url_end_idx > url_start_idx:
            end_idx = url_qmark_idx if url_qmark_idx > url_start_idx and url_qmark_idx < url_end_idx else url_end_idx
            release_url = message_text[url_start_idx:end_idx]
    return release_url


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

        
def get_widget_string(release_id, release_url, is_track):
    if is_track:
        return f'<iframe style="border: 0; width: 400px; height: 120px;" src="https://bandcamp.com/EmbeddedPlayer/track={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=false/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'
    else:
        return f'<iframe style="border: 0; width: 400px; height: 274px;" src="https://bandcamp.com/EmbeddedPlayer/album={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'



# ------------------------------------------------------------------------ GMAIL

# Request all access (permission to read/send/receive emails, manage the inbox, and more)
SCOPES = ['https://mail.google.com/']

def gmail_authenticate():
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)


def search_messages(service, query, max_results=100):
    result = service.users().messages().list(userId='me',q=query, maxResults=max_results).execute()
    messages = [ ]
    if 'messages' in result:
        messages.extend(result['messages'])
    while len(messages) < max_results and 'nextPageToken' in result:
        page_token = result['nextPageToken']
        result = service.users().messages().list(userId='me',q=query, pageToken=page_token).execute()
        if 'messages' in result:
            messages.extend(result['messages'])
    return messages


def get_messages(service, ids, format, max_results, before_date, after_date):    

    email_data_file = f'email_data_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}.pkl'
    
    if not use_cached_data:

        idx = 0
        raw_emails = {}

        while idx < len(ids):
            print(f'Downloading messages {idx} to {min(idx+100, len(ids))}')
            batch = service.new_batch_http_request()
            for id in ids[idx:idx+100]:
                batch.add(service.users().messages().get(userId = 'me', id = id, format=format))
            batch.execute()
            response_keys = [key for key in batch._responses]

            for key in response_keys:
                raw_email = json.loads(batch._responses[key][1])['raw']
                raw_emails[str(idx)] = base64.urlsafe_b64decode(raw_email + '=' * (4 - len(raw_email) % 4))
                idx += 1

        with open(f"data/{email_data_file}", "wb+") as a_file:
            pickle.dump(raw_emails, a_file)

    with open(f"data/{email_data_file}", "rb") as a_file:
        raw_emails = pickle.load(a_file)
    
    return raw_emails



# ------------------------------------------------------------------------ PARSING + PROCESSING

def parse_messages(raw_emails, max_results, before_date, after_date):
    
    print ('Parsing messages...')
    release_info_file = f'release_data_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}.pkl'
    
    if not use_cached_data:

        releases_unsifted = []

        # Parse emails for URL, image URL and date
        for _, email in raw_emails.items():
            s = email
            try:
                s = s.decode()
            except:
                s = str(s)
            release_url = parse_release_url(s)
            is_track = "bandcamp.com/track" in release_url

            # image url
            img_idx_end = s.find('jpg') + 3
            if img_idx_end == -1:
                print (f'img_idx_end not found for {release_url}')
                continue
            img_idx_start = s[0:img_idx_end].rfind('http')
            if img_idx_start == -1:
                print (f'img_idx_start not found for {release_url}')
                continue
            img_url = s[img_idx_start:img_idx_end]

            # date
            date_idx = s.find('X-Google-Smtp-Source')
            if date_idx == -1:
                print (f'date_idx not found for {release_url}')
                continue
            date_idx_start = s[0:date_idx-2].rfind('\n') + 2        
            if date_idx_start == -1:
                print (f'date_idx_start not found for {release_url}')
                continue
            date_len = s[date_idx_start:date_idx_start+200].find('\r')
            if date_len == -1:
                print (f'date_len not found for {release_url}')
                continue

            date_idx_end = date_idx_start + date_len
            date = s[date_idx_start:date_idx_end].strip().encode('utf-8').decode('unicode_escape')
            date = date[0:16]

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
            release_url = release['url']

            html_text = requests.get(release_url).text
            soup = BeautifulSoup(html_text, 'html.parser')

            # release title
            release_title = soup.find('h2', class_="trackTitle")
            if release_title is not None:
                release_title = soup.find('h2', class_="trackTitle").text.strip()        
            else:
                print(f'Release title not found at {release_url}')
                continue

            # artist name
            def parse_artist_name(input):
                input = input.strip()
                if (input[0:2] != 'by'):
                    return None
                input = input [2:]
                return input.strip()

            artist_name = soup.find('h3')

            if artist_name is not None:
                artist_name = parse_artist_name(soup.find('h3').text)
                if artist_name == None:
                    print(f'Error parsing artist name at {release_url}')
                    continue
            else:
                print(f'Artist name not found at {release_url}')
                continue

            # page name 
            page_name = soup.findAll('span', class_="title")
            if page_name is not None:
                page_name = page_name[1].text.strip()
            else:
                print(f'Page name not found at {release_url}')
                continue

            # release id
            release_id = soup.find('meta', attrs={'name':'bc-page-properties'})
            if release_id is not None:
                release_id = eval(release_id["content"])['item_id']
            else:
                print (f'release_id not found at {release_url}')
                continue
                
            release['artist_name'] = artist_name
            release['release_title'] = release_title
            release['page_name'] = page_name
            release['release_id'] = release_id

            print(f'Retrieving release data for {release_title} by {artist_name}')
        
        with open(f"data/{release_info_file}", "wb+") as a_file:
            pickle.dump(releases, a_file)

    with open(f"data/{release_info_file}", "rb") as a_file:
        releases = pickle.load(a_file)

    return releases



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
            release_id_1 = release1['release_id']
            release_id_2 = release2['release_id']
            release_url_1 = release1['url']
            release_url_2 = release2['url']
            is_track_1 = release1['is_track']
            is_track_2 = release2['is_track']
            date_1 = release1['date']
            date_2 = release2['date']
            page_url_1 = get_bc_page_url(release_url_1, is_track_1)
            page_url_2 = get_bc_page_url(release_url_2, is_track_2)
            page_name_1 = release1['page_name']
            page_name_2 = release2['page_name']
            widget_string_1 = get_widget_string(release_id_1, release_url_1, is_track_1)
            widget_string_2 = get_widget_string(release_id_2, release_url_2, is_track_2)
            doc += '<p>'
            doc += '<table>'
            doc += f'<b><tr><th>{date_1} / {page_name_1}</th> <th>{date_2} / {page_name_2}</th></tr></b>'
            doc += f'<tr><td align="center"><i><a href="{release_url_1}">{page_url_1}</a></i></td> <td align="center"><i><a href="{release_url_2}">{page_url_2}</a></i></td></tr>'
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



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Gmail for Bandcamp release notifications and generate an HTML file of Bandcamp player widgets.")
    
    max_results = 20
    after_date = '2022/03/01' # YYYY/MM/DD
    before_date = '2022/06/26' # YYYY/MM/DD
    results_pp = 100

    parser.add_argument("-e", "--earliest",     help="Earliest date",               default="",             type=str)
    parser.add_argument("-l", "--latest",       help="Latest date",                 default="today",        type=str)
    parser.add_argument("-m", "--max_results",  help="Maximum results to fetch",    default=2000,           type=int)
    parser.add_argument("-r", "--results_pp",   help="Results per output page",     default=50,             type=int)

    args = parser.parse_args()

    max_results = args.max_results
    after_date  = args.earliest
    before_date = args.latest if args.latest != "today" else f'{datetime.date.today().year}/{datetime.date.today().month:02d}/{datetime.date.today().day:02d}'
    results_pp  = args.results_pp

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
    output_dir_name = f'bandcamp_listings_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}'
    Path("data").mkdir(exist_ok=True)
    Path(output_dir_name).mkdir(exist_ok=True)

    # get the Gmail API service
    service = gmail_authenticate()

    # Do the thing
    search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{before_date} after:{after_date}"
    message_ids = search_messages(service, search_query, max_results=max_results)
    raw_emails = get_messages(service, [msg['id'] for msg in message_ids], 'raw', max_results, before_date, after_date)
    releases = parse_messages(raw_emails, max_results, before_date, after_date)
    generate_html(releases, output_dir_name, results_pp)
