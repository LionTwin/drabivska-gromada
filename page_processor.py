from bs4 import BeautifulSoup
from utils import fetch_with_retry
from requests.exceptions import RequestException
import logging

def fetch_page_data(url, lastmod):
    try:
        response = fetch_with_retry(url)
    except RequestException:
        logging.error(f"Failed to fetch {url} after multiple attempts")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    og_title = soup.find('meta', attrs={'property': 'og:title'})
    meta_description = soup.find('meta', attrs={'name': 'description'})

    title = og_title['content'] if og_title else soup.title.string if soup.title else "No Title"
    description = meta_description['content'] if meta_description else "No Description"

    return {
        "url": url,
        "title": title,
        "description": description,
        "time": lastmod
    }

def save_html_page(url, filename):
    response = fetch_with_retry(url)
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(response.text)