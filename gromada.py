import requests
from bs4 import BeautifulSoup
import json
import time as t
import os
from datetime import datetime
import telebot
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
import sys
import logging

# Основні параметри
SITEMAP_URL = "https://drabivska-gromada.gov.ua/sitemap.xml"
SITEMAP_FILE = "sitemap_local.xml"
PARSER_FILE = "parser.json"
NOINFORMED_URLS_FILE = "noinformed_urls.json"

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.info("Script started")

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if TELEGRAM_BOT_TOKEN is None or CHAT_ID is None:
    raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set. Please check your environment variables.")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment='')).rstrip('/').lower()

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

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"Error loading JSON from {filename}: {e}")
                return {}
    return {}

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

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

def fetch_page_data(url, lastmod):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        else:
            raise

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
    response = requests.get(url)
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(response.text)

def send_telegram_message(chat_id, message):
    while True:
        try:
            bot.send_message(chat_id, message, parse_mode='Markdown')
            print(f"Message sent to {chat_id}: {message}")
            break
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 429:
                retry_after = int(e.result_json['parameters']['retry_after'])
                t.sleep(retry_after)
            else:
                break

def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")

def load_noinformed_urls():
    if os.path.exists(NOINFORMED_URLS_FILE):
        with open(NOINFORMED_URLS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # Конвертуємо список у словник, якщо це список
            if isinstance(data, list):
                return {item['url']: item['timestamp'] for item in data}
            return data
    return {}

def save_noinformed_urls(noinformed_urls):
    with open(NOINFORMED_URLS_FILE, 'w', encoding='utf-8') as file:
        json.dump(noinformed_urls, file, ensure_ascii=False, indent=4)

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

            logging.info("Loading informed URLs")
            informed_urls = load_informed_urls()

            logging.info("Loading noinformed URLs")
            noinformed_urls = load_noinformed_urls()

            logging.info("Checking noinformed URLs")
            check_noinformed_urls(noinformed_urls, informed_urls)

            logging.info("Downloading sitemap")
            download_sitemap()

            logging.info("Parsing sitemap")
            sitemap_entries = parse_sitemap()

            logging.info("Loading old entries")
            old_entries = load_json('sitemap.json')

            logging.info("Comparing sitemaps")
            new_entries = compare_sitemaps(old_entries, sitemap_entries)
            logging.info(f"Found {len(new_entries)} new entries")

            logging.info("Save sitemap json")
            save_json(sitemap_entries, 'sitemap.json')

            for entry in new_entries:
                loc = entry['loc']
                normalized_loc = normalize_url(loc)
                logging.info(f"Processing new entry: {loc}")
                logging.info(f"Normalized URL: {normalized_loc}")

                if normalized_loc in informed_urls or normalized_loc in noinformed_urls:
                    logging.info(f"Skipping already processed URL: {normalized_loc}")
                    continue

                lastmod = entry['lastmod']
                filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
                html_filename = os.path.join('pages', filename)

                logging.info("Save html page")
                save_html_page(loc, html_filename)

                logging.info("Fetch html page data")
                try:
                    page_data = fetch_page_data(loc, lastmod)
                    if page_data:
                        formatted_date = format_date(page_data['time'])
                        message = f"_{formatted_date}_\n*{page_data['title']}*\n\n{page_data['description']}\n\n{page_data['url']}\n"
                        send_telegram_message(CHAT_ID, message)
                        informed_urls[normalized_loc] = lastmod
                    else:
                        noinformed_urls[normalized_loc] = lastmod
                        logging.info(f"URL {normalized_loc} returned 404, added to noinformed_urls")
                except Exception as e:
                    logging.error(f"Error processing {loc}: {e}")
                    noinformed_urls[normalized_loc] = lastmod

            logging.info("Save informed urls")
            save_informed_urls(informed_urls)

            logging.info("Save noinformed urls")
            save_noinformed_urls(noinformed_urls)

            logging.info("Main function completed")
            t.sleep(3600)  # Пауза на 1 годину

        except Exception as e:
            logging.error(f"Unhandled exception in main: {e}")
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