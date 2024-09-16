import requests
from bs4 import BeautifulSoup
from config import SITEMAP_URL, SITEMAP_FILE

def download_sitemap():
    response = requests.get(SITEMAP_URL)
    with open(SITEMAP_FILE, 'wb') as file:
        file.write(response.content)

def parse_sitemap():
    with open(SITEMAP_FILE, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, features='xml')
    sitemap_entries = []
    for url in soup.find_all('url'):
        loc = url.find('loc').text
        lastmod = url.find('lastmod').text if url.find('lastmod') else "No Lastmod"
        sitemap_entries.append({"loc": loc, "lastmod": lastmod})
    sitemap_entries.sort(key=lambda x: x['lastmod'])
    return sitemap_entries

def compare_sitemaps(old, new):
    old_set = {entry['loc'] for entry in old}
    return [entry for entry in new if entry['loc'] not in old_set]