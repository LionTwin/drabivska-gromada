import requests
from bs4 import BeautifulSoup
import json
import time as t
import os
from datetime import datetime
import telebot
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv

# Основні параметри
SITEMAP_URL = "https://drabivska-gromada.gov.ua/sitemap.xml"
SITEMAP_FILE = "sitemap_local.xml"
PARSER_FILE = "parser.json"

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
        if os.path.getsize('informed_urls.json') > 0:  # Перевірка, чи файл не порожній
            with open('informed_urls.json', 'r', encoding='utf-8') as file:
                return set(normalize_url(url) for url in json.load(file))
    return set()

# Збереження оброблених URL в JSON
def save_informed_urls(informed_urls):
    with open('informed_urls.json', 'w', encoding='utf-8') as file:
        json.dump(list(informed_urls), file, ensure_ascii=False, indent=4)

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
    if not os.path.exists('pages'):
        os.makedirs('pages')

    informed_urls = load_informed_urls()

    # Завантаження нових записів
    download_sitemap()
    sitemap_entries = parse_sitemap()

    # Завантаження існуючих записів у JSON
    old_entries = load_json('sitemap.json')

    # Порівняння старих і нових записів
    new_entries = compare_sitemaps(old_entries, sitemap_entries)

    # Збереження всіх записів у JSON
    save_json(sitemap_entries, 'sitemap.json')

    # Обробка нових записів
    for entry in new_entries:
        loc = entry['loc']
        normalized_loc = normalize_url(loc)

        # Перевірка, чи URL вже був оброблений
        if normalized_loc in informed_urls:
            continue

        informed_urls.add(normalized_loc)
        save_informed_urls(informed_urls)

        lastmod = entry['lastmod']
        filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
        html_filename = os.path.join('pages', filename)

        # Збереження HTML сторінки
        save_html_page(loc, html_filename)

        # Отримання даних зі сторінки
        page_data = fetch_page_data(loc, lastmod)

        if page_data:
            # Відправка повідомлення в Telegram
            formatted_date = format_date(page_data['time'])
            message = f"_{formatted_date}_\n*{page_data['title']}*\n\n{page_data['description']}\n\n{page_data['url']}\n"
            send_telegram_message(CHAT_ID, message)
        else:
            print(f"Не вдалося отримати дані для {loc}.")

if __name__ == "__main__":
    main()