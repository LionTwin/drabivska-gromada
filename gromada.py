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

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.info("Script started")

load_dotenv()
# Отримання TELEGRAM_BOT_TOKEN і CHAT_ID зі змінних середовища
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Перевірка наявності необхідних змінних середовища
if TELEGRAM_BOT_TOKEN is None:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set. Please check your environment variables.")
if CHAT_ID is None:
    raise ValueError("TELEGRAM_CHAT_ID is not set. Please check your environment variables.")

# Ініціалізація бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Нормалізація URL
def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment='')).rstrip('/').lower()

# Завантаження оброблених URL з JSON
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

# Збереження оброблених URL в JSON
def save_informed_urls(informed_urls):
    logging.info(f"Saving {len(informed_urls)} informed URLs")
    urls_data = [{'url': url, 'timestamp': timestamp} for url, timestamp in informed_urls.items()]
    with open('informed_urls.json', 'w', encoding='utf-8') as file:
        json.dump(urls_data, file, ensure_ascii=False, indent=4)
    logging.info("Informed URLs saved successfully")

# Завантаження JSON даних
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"Error loading JSON from {filename}: {e}")
                return {}
    return {}

# Збереження даних у форматі JSON
def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Завантаження та парсинг SITEMAP
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

# Порівняння старих і нових записів
def compare_sitemaps(old, new):
    old_set = {entry['loc'] for entry in old}
    return [entry for entry in new if entry['loc'] not in old_set]

# Отримання даних зі сторінки
def fetch_page_data(url, lastmod):
    response = requests.get(url)
    if response.status_code == 404:
        return None  # Якщо сторінка не існує

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

# Збереження HTML сторінки
def save_html_page(url, filename):
    response = requests.get(url)
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(response.text)

# Відправка повідомлення в Telegram
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

# Форматування дати у вигляді dd.mm.yyyy
def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")

# Основна функція
def main():
    while True:
        try:
            logging.info("Starting main function")
            if not os.path.exists('pages'):
                os.makedirs('pages')

            logging.info("Loading informed URLs")
            try:
                informed_urls = load_informed_urls()
            except Exception as e:
                logging.error(f"Error loading informed URLs: {e}")
                return

            # Завантаження нових записів
            logging.info("Downloading sitemap")
            try:
                download_sitemap()
            except Exception as e:
                logging.error(f"Error downloading sitemap: {e}")
                return

            logging.info("Parsing sitemap")
            try:
                sitemap_entries = parse_sitemap()
            except Exception as e:
                logging.error(f"Error parsing sitemap: {e}")
                return

            # Завантаження існуючих записів у JSON
            logging.info("Loading old entries")
            try:
                old_entries = load_json('sitemap.json')
            except Exception as e:
                logging.error(f"Error loading old entries: {e}")
                return

            # Порівняння старих і нових записів
            logging.info("Comparing sitemaps")
            try:
                new_entries = compare_sitemaps(old_entries, sitemap_entries)
            except Exception as e:
                logging.error(f"Error comparing sitemaps: {e}")
                return
            logging.info(f"Found {len(new_entries)} new entries")

            # Збереження всіх записів у JSON
            logging.info("Save sitemap json")
            try:
                save_json(sitemap_entries, 'sitemap.json')
            except Exception as e:
                logging.error(f"Error save sitemap json: {e}")
                return

            # Обробка нових записів
            for entry in new_entries:
                loc = entry['loc']
                logging.info("Normalize url")
                try:
                    normalized_loc = normalize_url(loc)
                except Exception as e:
                    logging.error(f"Error save sitemap json: {e}")
                    return
                logging.info(f"Processing new entry: {loc}")
                logging.info(f"Normalized URL: {normalized_loc}")

                # Перевірка, чи URL вже був оброблений
                if normalized_loc in informed_urls:
                    continue

                logging.info("Add informed urls")
                try:
                    informed_urls.add(normalized_loc)
                except Exception as e:
                    logging.error(f"Error add informed urls: {e}")
                    return

                logging.info("Save informed urls")
                try:
                    save_informed_urls(informed_urls)
                except Exception as e:
                    logging.error(f"Error save informed urls: {e}")
                    return

                lastmod = entry['lastmod']
                filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
                html_filename = os.path.join('pages', filename)

                # Збереження HTML сторінки
                logging.info("Save html page")
                try:
                    save_html_page(loc, html_filename)
                except Exception as e:
                    logging.error(f"Error save html page: {e}")
                    return

                # Отримання даних зі сторінки
                logging.info("Fetch html page data")
                try:
                    page_data = fetch_page_data(loc, lastmod)
                except Exception as e:
                    logging.error(f"Error fetch html page data: {e}")
                    return

                if page_data:
                    # Відправка повідомлення в Telegram
                    logging.info("Send Telegram message")
                    formatted_date = format_date(page_data['time'])
                    message = f"_{formatted_date}_\n*{page_data['title']}*\n\n{page_data['description']}\n\n{page_data['url']}\n"
                    logging.info("Send Telegram message")
                    try:
                        send_telegram_message(CHAT_ID, message)
                    except Exception as e:
                        logging.error(f"Error sending Telegram message: {e}")
                        return
                else:
                    print(f"Не вдалося отримати дані для {loc}.")
                logging.info("Main function completed")
            t.sleep(3600)  # Пауза на 1 годину
        except Exception as e:
            logging.error(f"Unhandled exception in main: {e}")
            print(f"An error occurred: {e}")
        finally:
            logging.info("Main function finished")
        t.sleep(300)  # Пауза на 5 хвилини перед повторною спробою

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