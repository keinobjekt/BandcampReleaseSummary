import pickle
import os
import base64
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ------------------------------------------------------------------------ 

k_gmail_credentials_file = "credentials.json"

# ------------------------------------------------------------------------ 
def gmail_authenticate():
    SCOPES = ['https://mail.google.com/'] # Request all access (permission to read/send/receive emails, manage the inbox, and more)

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
            flow = InstalledAppFlow.from_client_secrets_file(k_gmail_credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

# ------------------------------------------------------------------------ 
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

# ------------------------------------------------------------------------ 
def get_messages(service, ids, format, batch_size):
    idx = 0
    raw_emails = {}

    while idx < len(ids):
        print(f'Downloading messages {idx} to {min(idx+batch_size, len(ids))}')
        batch = service.new_batch_http_request()
        for id in ids[idx:idx+batch_size]:
            batch.add(service.users().messages().get(userId = 'me', id = id, format=format))
        batch.execute()
        response_keys = [key for key in batch._responses]

        for key in response_keys:
            email_data = json.loads(batch._responses[key][1])
            if 'error' in email_data:
                err_msg = email_data['error']['message']
                if email_data['error']['code'] == 429:
                    raise Exception(f"{err_msg} Try reducing batch size using argument --batch.")
                else:
                    raise Exception(err_msg)
            raw_email = email_data['raw']
            raw_emails[str(idx)] = base64.urlsafe_b64decode(raw_email + '=' * (4 - len(raw_email) % 4))
            idx += 1

    return raw_emails



# ------------------------------------------------------------------------ 
# Scrape Bandcamp URL, date and image URL from one email
def scrape_info_from_email(email_text):
    date = None
    img_url = None
    release_url = None
    is_track = None

    s = email_text
    try:
        s = s.decode()
    except:
        s = str(s)
    
    # release url
    release_url = None
    search_string = 'a href="https://'
    start_idx = s.find(search_string)
    if start_idx >= 0:
        url_start_idx = s.find(search_string) + 8
        url_end_idx = s.find('"', url_start_idx)
        url_qmark_idx = s.find('?', url_start_idx)
        if url_end_idx > url_start_idx:
            end_idx = url_qmark_idx if url_qmark_idx > url_start_idx and url_qmark_idx < url_end_idx else url_end_idx
            release_url = s[url_start_idx:end_idx]

    if release_url == None:
        return None, None, None, None

    # track (vs release) flag
    is_track = "bandcamp.com/track" in release_url

    # image url
    img_idx_end = s.find('jpg') + 3
    if img_idx_end == -1:
        print (f'img_idx_end not found for {release_url}')
        return None, None, None, None
    img_idx_start = s[0:img_idx_end].rfind('http')
    if img_idx_start == -1:
        print (f'img_idx_start not found for {release_url}')
        return None, None, None, None
    img_url = s[img_idx_start:img_idx_end]

    # Date
    date_idx = s.find('X-Google-Smtp-Source')
    if date_idx == -1:
        print (f'date_idx not found for {release_url}')
        return None, None, None, None
    
    # Expected format for s[0:date_idx-2]
    # case 1: "Delivered-To: keinobjekt@gmail.com\r\nReceived: by 2002:a05:7300:2552:b0:110:3fe2:a0ef with SMTP id p18csp1012723dyi;\r\n        Thu, 30 May 2024 01:47:47 -0700 (PDT)"
    #   OR
    # case 2: "b'Delivered-To: keinobjekt@gmail.com\\r\\nReceived: by 2002:a05:7300:2552:b0:110:3fe2:a0ef with SMTP id p18csp1064864dyi;\\r\\n        Thu, 30 May 2024 04:15:32 -0700 (PDT)\\r"
    date_idx_start = s[0:date_idx-2].rfind('\n') # try case 1 first
    if date_idx_start == -1:
        date_idx_start = s[0:date_idx-2].rfind('\\n') # try case 2
        if date_idx_start ==-1:
            print (f'date_idx_start not found for {release_url}')
            return None, None, None, None
    date_idx_start += 2
    
    # Expected format for s[date_idx_start:date_idx_start+200]:
    # case 1: "       Thu, 30 May 2024 11:43:44 -0700 (PDT)\r\nX-Google-Smtp-Source: AGHT+IHRXYFV86BGPusTN6HQR23/ZruHYVVKf68vtBTpgWGtmTtHLURVYkoj4LmZlbCCgXhF5Hpf\r\nX-Received: by 2002:a05:620a:1aa3:b0:794:f353:4bfd wit"
    # case 2: "       Thu, 30 May 2024 15:14:16 -0700 (PDT)\\r\\nX-Google-Smtp-Source: AGHT+IGYSvmcyxdro1Quw1bBrSHLfS9jj55klik3GxISEk/3UOyHA21h2zzRLk0oCmJjFSfNIDde\\r\\nX-Received: by 2002:ac8:7c47:0:b0:43e:26ab:4fbc w"
    date_len = s[date_idx_start:date_idx_start+200].find('\r') # try case 1
    if date_len == -1:
        date_len = s[date_idx_start:date_idx_start+200].find('\\r') # try case 2
        if date_len == -1:
            print (f'date_len not found for {release_url}')
            return None, None, None, None

    date_idx_end = date_idx_start + date_len
    date = s[date_idx_start:date_idx_end].strip().encode('utf-8').decode('unicode_escape')
    date = date[0:16]

    return date, img_url, release_url, is_track
