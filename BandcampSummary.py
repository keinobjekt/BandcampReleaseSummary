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

        greetings_string = f'Greetings {our_username},'
        loc_greetings = s.find(greetings_string)

        if loc_greetings <= 0:
            continue # no "Greetings username" found

        # check if greetings string is followed by \r\n or \\r\\n
        idx_after_greetings = loc_greetings+len(greetings_string)
        after_greetings_string = s[idx_after_greetings:idx_after_greetings+4]
        if '\r\n' in after_greetings_string:
            double_esc = False
            page_start_idx = idx_after_greetings + 2
            lf_char = '\n'
            cr_char = '\r'
        elif '\\r\\n' in after_greetings_string:
            double_esc = True
            page_start_idx = idx_after_greetings + 4
            lf_char = '\\n'
            cr_char = '\\r'

        if s[page_start_idx:].find(' just announced') > 0:
            continue # this is announcement email not a release email

        # image
        img_idx_end = s.find('jpg') + 3
        img_idx_start = s[0:img_idx_end].rfind('http')
        img_url = s[img_idx_start:img_idx_end]

        # date
        date_idx = s.find('X-Google-Smtp-Source')
        date_idx_start = s[0:date_idx-2].rfind(lf_char) + 2        
        date_len = s[date_idx_start:date_idx_start+200].find(cr_char)
        date_idx_end = date_idx_start + date_len
        date = s[date_idx_start:date_idx_end].lstrip()

        if s[page_start_idx:].find(' just released the following:') > 0:
            title_in_quotes = False

            # page
            page_start_idx += 2 * (len(lf_char) + len(cr_char)) # crop '\r\n\r\n'
            page_name_length = s[page_start_idx:].find(' just released the following:')
            page_end_idx = page_start_idx + page_name_length
            page = s[page_start_idx:page_end_idx]

            # release
            release_start_idx = page_end_idx + len(' just released the following:')
            
            # crop some leading line breaks
            def count_line_break_chars(string, start_idx):
                offs = 0
                while cr_char in string[start_idx+offs:start_idx+offs+2] or lf_char in string[start_idx+offs:start_idx+offs+2]:
                    offs += 2
                return offs

            release_start_idx += count_line_break_chars(s, release_start_idx)
            release_end_idx = release_start_idx + s[release_start_idx:].find(f'{cr_char}{lf_char}')
            release = s[release_start_idx : release_end_idx]
            
            # url
            url_start_idx = release_end_idx + (4 if double_esc else 2)
            url_end_idx = url_start_idx + s[url_start_idx:].find('?')
            url = s[url_start_idx:url_end_idx]

        elif s[page_start_idx:].find(' just released') > 0:
            title_in_quotes = True

            # page
            page_name_length = s[page_start_idx:].find(' just released')
            page_end_idx = page_start_idx + page_name_length
            page = s[page_start_idx:page_end_idx]

            # release
            release_start_idx = page_end_idx + len(' just released ')
            release_end_idx = release_start_idx + s[release_start_idx:].find('check it out') - 2
            release = s[release_start_idx : release_end_idx]
            
            # url
            url_offset = s[release_end_idx:].find(lf_char) + (2 if double_esc else 1)
            url_start_idx = release_end_idx + url_offset
            url_end_idx = url_start_idx + s[url_start_idx:].find('?')
            url = s[url_start_idx:url_end_idx]
        else:
            continue # probably "just added"

        # split release='X by Y' into title=X, artist=Y
        if 'by' in release:
            if title_in_quotes:
                title = release[0:release.find('" by') + 1]
                artist = release[release.find('" by') + 5:]
            else:
                title = release[0:release.rfind(' by ')]
                artist = release[release.rfind(' by ') + 4:]
        else:
            title = release
            artist = None

        release_dict = {}
        release_dict['img_url'] = img_url
        release_dict['date'] = date.encode('utf-8').decode('unicode_escape')
        release_dict['artist'] = artist.encode('utf-8').decode('unicode_escape') if artist is not None else None
        release_dict['title'] = title.encode('utf-8').decode('unicode_escape')
        release_dict['label'] = page.encode('utf-8').decode('unicode_escape')
        release_dict['url'] = url
        releases[str(idx)] = release_dict

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
