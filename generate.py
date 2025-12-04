from util import construct_release

# ------------------------------------------------------------------------ 
def get_widget_string(release_id, release_url, is_track):
    if is_track:
        return f'<iframe style="border: 0; width: 400px; height: 120px;" src="https://bandcamp.com/EmbeddedPlayer/track={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=false/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'
    else:
        return f'<iframe style="border: 0; width: 400px; height: 274px;" src="https://bandcamp.com/EmbeddedPlayer/album={release_id}/size=large/bgcol=ffffff/linkcol=0687f5/artwork=small/transparent=true/" seamless><a href="{release_url}"></a></iframe>'

 
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