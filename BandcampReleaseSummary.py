import pickle
import argparse
import datetime
from pathlib import Path

from gmail import gmail_authenticate, search_messages, get_messages, scrape_info_from_email
from bandcamp import scrape_info_from_bc_page
from util import construct_release
from generate import generate_html

## Settings ##
k_no_download = False
k_data_dir = "data"
k_output_path = "output"


# ------------------------------------------------------------------------ 
# Create a list of releases with metadata
def construct_release_list(emails):

    print ('Parsing messages...')
    releases_unsifted = []
    for _, email in emails.items():
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
            emails = pickle.load(a_file)
    else:
        emails = get_messages(service, [msg['id'] for msg in message_ids], 'full', batch_size)

        with open(f"{k_data_dir}/{email_data_file}", "wb+") as a_file:
            pickle.dump(emails, a_file)
    
    # Compile list of releases
    release_info_file = f'release_data_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}.pkl'
    if k_no_download:
        print ('Opening saved release list...')
        with open(f"{k_data_dir}/{release_info_file}", "rb") as a_file:
            releases = pickle.load(a_file)
    else:
        releases = construct_release_list(emails)
        with open(f"{k_data_dir}/{release_info_file}", "wb+") as a_file:
            pickle.dump(releases, a_file)
    
    # Generate HTML pages
    generate_html(releases, output_dir_name, results_pp)
