import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type

import base64
from html import unescape

import requests
from bs4 import BeautifulSoup

import json

# Request all access (permission to read/send/receive emails, manage the inbox, and more)
SCOPES = ['https://mail.google.com/']
our_email = 'keinobjekt@gmail.com'
max_results = 20
our_username = 'tjhertz'



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

def get_message(service, id, format):
    return service.users().messages().get(userId='me', id=id, format=format).execute()


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


def get_payload(request_id, response, exception):
    if exception is not None:
    # Do something with the exception
        pass
    else:
    # Do something with the response
        return response['payload']

def get_messages(service, ids, format):    

    idx = 0
    raw_emails = {}

    while idx < len(ids):
        print(f'Downloading messages {idx} to {min(idx+100, len(ids))}')
        batch = service.new_batch_http_request()
        for id in ids[idx:idx+100]:
            batch.add(service.users().messages().get(userId = 'me', id = id, format=format))#, callback=get_payload)
        batch.execute()
        response_keys = [key for key in batch._responses]

        for key in response_keys:
            raw_email = json.loads(batch._responses[key][1])['raw']
            raw_emails[str(idx)] = base64.urlsafe_b64decode(raw_email + '=' * (4 - len(raw_email) % 4))
            idx += 1

    import pickle

    with open("data.pkl", "wb") as a_file:
        pickle.dump(raw_emails, a_file)

    with open("data.pkl", "rb") as a_file:
        raw_emails = pickle.load(a_file)
    
    return raw_emails


        
def parse_messages(raw_emails):
    releases = {}

    for idx, email in raw_emails.items():

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

        release = {}
        release['img_url'] = img_url
        release['date'] = date
        release['artist'] = artist_name
        release['title'] = release_title
        release['label'] = page_name
        release['url'] = release_url
        releases[str(idx)] = release

    return releases

def get_label(messages):
    
    return 0


if __name__ == "__main__":
    # get the Gmail API service
    service = gmail_authenticate()

    search_query = f"from:noreply@bandcamp.com subject:'New release from'"

    message_ids = search_messages(service, search_query, max_results=max_results)

    raw_emails = get_messages(service, [msg['id'] for msg in message_ids], 'raw')
    messages = parse_messages(raw_emails)

    import pandas as pd
    def path_to_image_html(path):
        return '<img src="'+ path + '" width="60">'
    df = pd.DataFrame.from_dict(messages).transpose()
    df.to_html('output.html', render_links=True, formatters=dict(img_url=path_to_image_html), escape=False)
