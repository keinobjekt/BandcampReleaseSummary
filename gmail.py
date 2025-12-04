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
