import pickle
import os
import base64
import json
import quopri
from furl import furl
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup

# ------------------------------------------------------------------------ 

k_gmail_credentials_file = "credentials.json"


# ------------------------------------------------------------------------ 
def get_html_from_message(msg):
    """
    Extracts and decodes the HTML part from a Gmail 'full' message.
    Always returns a proper Unicode string (or None).
    """
    def walk_parts(part):
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")

        # If this part is HTML, decode it
        if mime_type == "text/html" and data:
            # Base64-url decode
            decoded_bytes = base64.urlsafe_b64decode(data)

            # Some Gmail messages use quoted-printable encoding inside HTML
            try:
                decoded_bytes = quopri.decodestring(decoded_bytes)
            except:
                pass

            # Convert to Unicode
            return decoded_bytes.decode("utf-8", errors="replace")

        # Multipart → recursive search
        for p in part.get("parts", []):
            html = walk_parts(p)
            if html:
                return html

        return None

    return walk_parts(msg["payload"])

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
    emails = {}

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
            email = get_html_from_message(email_data)
            emails[str(idx)] = email
            idx += 1

    return emails



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
    soup = BeautifulSoup(email_text, "html.parser") if email_text else None
    release_url = None

    def _find_bandcamp_release_url() -> str | None:
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Basic heuristic for Bandcamp release pages
            if "bandcamp.com" in href and ("/album/" in href or "/track/" in href):
                return furl(href).remove(args=True, fragment=True).url
        return None
    
    release_url = _find_bandcamp_release_url()

    if release_url == None:
        return None, None, None, None

    # track (vs release) flag
    is_track = "bandcamp.com/track" in release_url

    # image url
    # img_idx_end = s.find('jpg') + 3
    # if img_idx_end == -1:
    #     print (f'img_idx_end not found for {release_url}')
    #     return None, None, None, None
    # img_idx_start = s[0:img_idx_end].rfind('http')
    # if img_idx_start == -1:
    #     print (f'img_idx_start not found for {release_url}')
    #     return None, None, None, None
    # img_url = s[img_idx_start:img_idx_end]

    return date, img_url, release_url, is_track
