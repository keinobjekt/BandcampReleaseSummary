# BANDCAMP RELEASE SUMMARY

BandcampReleaseSummary.py is a Python script which scrapes the Bandcamp release notification emails in your GMail account within a given date range, in order to create an HTML summary of new releases which can be opened in your browser.

The output file succinctly lists the new releases in an easy-to-browse format with a preview player widget for each release.

DISCLAIMER: The script was written quickly for my own convenience and the code is quite naive in many places. It comes with absolutely no guarantee and will almost certainly break in the future whenever the formatting of the BC release notifaction emails changes (as it sometimes does). Use entirely at your own risk. 


# INSTRUCTIONS

IMPORTANT: It is assumed that you have a basic familiarity with Python and already have Python and Pip installed on your machine.

Due to not yet being officially verified by Google, this script requires a bit of setup in order to use, but it's pretty straightforward and most of this only needs to be done once.

You'll need to:

- Set up a virtual environment with all the necessary Python dependencies installed
- Set up GMail authentication to give the script access to your GMail account

Just follow all the steps below. 


## Set up virtual environment and install dependencies

1. Create a virtual env and activate it. To do this, navigate to the script directory and type the following into a Terminal window:

    pip3 install virtualenv
    virtualenv venv
    source venv/bin/activate

2. Install the BandcampReleaseSummary dependencies by typing the following into Terminal:
    
    venv/bin/pip install -r requirements.txt


## Set up GMail authentication

Because this script hasn't been officially verified by Google for public use, there are some extra steps you'll need to take in order to give it access to your Gmail – essentially you'll be using the Gmail API as a developer/tester rather than an end-user so you have to create access credentials on the Google Cloud Console.

Here is a walkthrough:

### Log in to GCP account
1. Go to https://console.cloud.google.com/
2. Sign in with the Google/Gmail account that receives your Bandcamp release notification emails
3. Click "Next" / "Not Now" / etc through any first-time setup screens if shown

### Create GCP project
4. At the top of the page, in between the Google Cloud logo and the search bar, click the "Select a project" dropdown menu.
5. At the top right of the dialog that opens up, click "New Project".
6. Name the project BandcampReleaseSummary and leave the location as "No organisation", then click Create and wait for the project to be created.

### Add GMail API to GCP project
7. Click the hamburger menu icon at the top left and click "APIs and Services". Select the BandcampReleaseSummary project.
8. Click Library at the left, then under "Welcome to the API Library", search for "GMail API".
9. Click through to the GMail API page, then click Enable.

### Configure OAuth consent screen
10. Now click the hamburger menu at the top left again, click "APIs and Services", and click OAuth Consent Screen.
11. Set the User Type to "External" and click Create.
12. In the OAuth consent screen setup page, name the app Bandcamp Summary, enter your own Gmail address in the User Support Email and Developer Contact Email fields, leave the rest blank, and click "Save and Continue".
12. Now, on the Scopes page, click Add or Remove Scopes. An "Update selected scopes" dialog will pop up with a list of scopes. Click through to the 2nd or 3rd page until you see "Gmail API – .../auth/gmail.readonly - View your email messages and settings". Select this and click the "Update" button at the bottom. This will close the popup and add that scope to your Restricted Scopes. Click Save and Continue.
13. On the Test Users page, just click Save and Continue.

### Create credentials
14. Click Credentials in the left menu. Click "+ Create Credentials" and click "OAuth client ID".
15. Under Application Type select "Desktop App" and leave the name as Desktop client 1. Click "Create".
16. In the "OAuth Client Created" popup that shows, click "Download JSON" and save the credentials file in the same directory as the BandcampReleaseSummary script, with the filename "credentials.json" (you can use any name but you'll have to edit "k_gmail_credentials_file" in the script accordingly).


## Run the BandcampReleaseSummary script ##

Now you're ready to run the Python script! Ensure the virtualenv is activated first: 
    
    source venv/bin/activate

Then type the following into a Terminal window, replacing "--earlieset" and "--latest" with your desired date range (in the format YYYY/MM/DD). The "--latest" argument defaults to today's date, so you don't need to enter it if you just want to summarize (e.g.) the last 2 months of releases.

    python3 BandcampReleaseSummary.py --earliest --latest

The first time you run the script, a browser window will pop up and you'll be prompted to enter your Google account credentials. Enter these and you're all set – for now. The output HTML files will be created in a new subdirectory.

Note: by default, only the first 2000 results will be compiled. This can be changed if desired using the --max_results argument. I would recommend keeping the date range (and max_results) fairly limited, e.g. a few months maximum. 


### Refresh the authorization credentials as needed

The script creates a local auth token for your GMail account, saved in the script directory as "token.pickle", which will remain valid for a finite period of time (I think it's 7 days). After it expires, running the script will throw an exception. When this happens, you'll have to delete the "credentials.json" file that you saved, along with the "token.pickle" file generated by the script. Then you'll need to create new credentials by repeating steps 14 onwards, which will create a new set of credentials each time (the new sets of credentials will automatically be named Desktop Client 2, Desktop Client 3, etc). Download the credentials you've just created (saving as credentials.json again), run the script (which will open a browser window prompting you to authorize again) and it should work again.