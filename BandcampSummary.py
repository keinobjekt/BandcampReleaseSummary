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


# Arguments
our_email = 'keinobjekt@gmail.com'
max_results = 20
before_date = '2022/04/20' # YYYY/MM/DD
after_date = '2022/03/20' # YYYY/MM/DD


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


def get_messages(service, ids, format):    

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

    import pickle

    with open("email_data.pkl", "wb") as a_file:
        pickle.dump(raw_emails, a_file)

    with open("email_data.pkl", "rb") as a_file:
        raw_emails = pickle.load(a_file)
    
    return raw_emails

def construct_release(img_url=None, date=None, artist_name=None, release_title=None, page_name=None, release_url=None, release_id=None):
    release = {}
    release['img_url'] = img_url
    release['date'] = date
    release['artist'] = artist_name
    release['title'] = release_title
    release['label'] = page_name
    release['url'] = release_url
    release['release_id'] = release_id
    return release
        
def parse_messages(raw_emails):
    releases = []

    for _, email in raw_emails.items():

        s = email

        try:
            s = s.decode()
        except:
            s = str(s)

        release_url = parse_release_url(s)

        html_text = requests.get(release_url).text
        soup = BeautifulSoup(html_text, 'html.parser')

        # release title
        release_title = soup.find('h2', class_="trackTitle").text.strip()        

        # artist name
        def parse_artist_name(input):
            input = input.strip()
            assert input[0:2] == 'by'
            input = input [2:]
            return input.strip()

        artist_name = parse_artist_name(soup.find('h3').text)

        # page name 
        page_name = soup.findAll('span', class_="title")[1].text.strip()

        # image url
        img_idx_end = s.find('jpg') + 3
        img_idx_start = s[0:img_idx_end].rfind('http')
        img_url = s[img_idx_start:img_idx_end]

        # date
        date_idx = s.find('X-Google-Smtp-Source')
        date_idx_start = s[0:date_idx-2].rfind('\n') + 2        
        date_len = s[date_idx_start:date_idx_start+200].find('\r')
        date_idx_end = date_idx_start + date_len
        date = s[date_idx_start:date_idx_end].strip().encode('utf-8').decode('unicode_escape')
        date = date[0:16]

        # release id
        release_id = eval(soup.find('meta', attrs={'name':'bc-page-properties'})["content"])['item_id']

        releases.append(construct_release(img_url, date, artist_name, release_title, page_name, release_url, release_id))

        print(f'Retrieving release data for {release_title} by {artist_name}')
    
    with open("release_data.pkl", "wb") as a_file:
        pickle.dump(releases, a_file)

    with open("release_data.pkl", "rb") as a_file:
        releases = pickle.load(a_file)

    return releases


def get_widget_string(release_id, release_url):
    return f'<iframe style="border: 0; width: 400px; height: 274px;" src="https://bandcamp.com/EmbeddedPlayer/album={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/artwork=small/transparent=true/" seamless><a href="{release_url}">4 Star Volume 3 by Bay B Kane</a></iframe>'


def generate_html(releases):

    odd_num_releases = len(releases) % 2 != 0
    if odd_num_releases: # append blank release to ensure releases list has an even number
        releases.append(construct_release())

    doc = '<html>'
    doc += '<body>'

    it = iter(releases)
    for release1 in it:
        release2 = next(it)
        release_id_1 = release1['release_id']
        release_id_2 = release2['release_id']
        release_url_1 = release1['url']
        release_url_2 = release2['url']
        date_1 = release1['date']
        date_2 = release2['date']
        url_1 = release1['url']
        url_2 = release2['url']
        label_1 = release1['label']
        label_2 = release2['label']
        widget_string_1 = get_widget_string(release_id_1, release_url_1)
        widget_string_2 = get_widget_string(release_id_2, release_url_2)
        doc += '<p>'
        doc += '<table>'
        doc += f'<tr><th><a href="{url_1}">{date_1} / {label_1}<a></th> <th><a href="{url_2}">{date_2} / {label_2}</a></th></tr>'
        doc += f'<tr><th>{widget_string_1}</th><th>{widget_string_2}</th></tr>'
        doc += '</table>'
        doc += '</p>'

    doc += '</body>'
    doc += '</html>'

    return doc


if __name__ == "__main__":
    # get the Gmail API service
    service = gmail_authenticate()

    search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{before_date} after:{after_date}"

    message_ids = search_messages(service, search_query, max_results=max_results)
    raw_emails = get_messages(service, [msg['id'] for msg in message_ids], 'raw')
    releases = parse_messages(raw_emails)
    html_data = generate_html(releases)

    with open('output.html', 'w') as file:
        file.write(html_data)
