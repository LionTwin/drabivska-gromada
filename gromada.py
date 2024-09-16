import json
import requests
import os
import time as t
import logging
import sys
from requests.exceptions import RequestException
from datetime import datetime
from config import CHAT_ID, NOINFORMED_URLS_FILE
from utils import normalize_url, load_json, save_json
from sitemap_parser import download_sitemap, parse_sitemap
from page_processor import fetch_page_data, save_html_page
from telegram_bot import send_telegram_message

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def load_informed_urls():
    if os.path.exists('informed_urls.json'):
        if os.path.getsize('informed_urls.json') > 0:
            with open('informed_urls.json', 'r', encoding='utf-8') as file:
                urls_data = json.load(file)
                informed_urls = {normalize_url(item['url']): item['timestamp'] for item in urls_data}
                logging.info(f"Loaded {len(informed_urls)} informed URLs")
                return informed_urls
    logging.info("No informed URLs loaded")
    return {}

def save_informed_urls(informed_urls):
    logging.info(f"Saving {len(informed_urls)} informed URLs")
    urls_data = [{'url': url, 'timestamp': timestamp} for url, timestamp in informed_urls.items()]
    with open('informed_urls.json', 'w', encoding='utf-8') as file:
        json.dump(urls_data, file, ensure_ascii=False, indent=4)
    logging.info("Informed URLs saved successfully")

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")

def load_noinformed_urls():
    if os.path.exists(NOINFORMED_URLS_FILE):
        with open(NOINFORMED_URLS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                return {item['url']: item['timestamp'] for item in data}
            return data
    return {}

def check_noinformed_urls(noinformed_urls, informed_urls):
    urls_to_remove = []
    for url, timestamp in noinformed_urls.items():
        try:
            response = requests.head(url)
            if response.status_code != 404:
                page_data = fetch_page_data(url, timestamp)
                if page_data:
                    formatted_date = format_date(page_data['time'])
                    message = f"_{formatted_date}_\n*{page_data['title']}*\n\n{page_data['description']}\n\n{page_data['url']}\n"
                    send_telegram_message(CHAT_ID, message)
                    informed_urls[url] = timestamp
                    urls_to_remove.append(url)
        except requests.RequestException:
            continue

    for url in urls_to_remove:
        del noinformed_urls[url]

def main():
    while True:
        try:
            logging.info("Starting main function")
            if not os.path.exists('pages'):
                os.makedirs('pages')

            informed_urls = load_informed_urls()
            noinformed_urls = load_noinformed_urls()
            check_noinformed_urls(noinformed_urls, informed_urls)

            download_sitemap()
            sitemap_entries = parse_sitemap()

            for entry in sitemap_entries:
                loc = entry['loc']
                normalized_loc = normalize_url(loc)
                logging.info(f"Processing entry: {loc}")

                if normalized_loc in informed_urls:
                    logging.info(f"Skipping already informed URL: {normalized_loc}")
                    continue

                if normalized_loc in noinformed_urls:
                    logging.info(f"URL {normalized_loc} was previously non-informed, rechecking")
                    del noinformed_urls[normalized_loc]

                lastmod = entry['lastmod']
                filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
                html_filename = os.path.join('pages', filename)

                try:
                    page_data = fetch_page_data(loc, lastmod)
                    if page_data:
                        formatted_date = format_date(page_data['time'])
                        message = f"_{formatted_date}_\n*{page_data['title']}*\n\n{page_data['description']}\n\n{page_data['url']}\n"
                        send_telegram_message(CHAT_ID, message)
                        informed_urls[normalized_loc] = lastmod

                        try:
                            save_html_page(loc, html_filename)
                        except RequestException:
                            logging.error(f"Failed to save HTML for {loc}")
                    else:
                        noinformed_urls[normalized_loc] = lastmod
                        logging.info(f"URL {normalized_loc} returned no data, added to noinformed_urls")
                except Exception as e:
                    logging.error(f"Error processing {loc}: {e}")
                    noinformed_urls[normalized_loc] = lastmod

            save_informed_urls(informed_urls)
            save_json(noinformed_urls, NOINFORMED_URLS_FILE)

            logging.info("Main function completed")
            t.sleep(900)  # Пауза на 15 хвилин

        except Exception as e:
            logging.error(f"Unhandled exception in main: {e}", exc_info=True)
            print(f"An error occurred: {e}")
        finally:
            logging.info("Main function finished")

        t.sleep(300)  # Пауза на 5 хвилин перед повторною спробою

if __name__ == "__main__":
    try:
        logging.info("Entering main block")
        main()
    except Exception as e:
        logging.error(f"An unhandled exception occurred: {e}")
    finally:
        logging.info("Script finished, waiting indefinitely")
        while True:
            t.sleep(3600)