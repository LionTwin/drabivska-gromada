# Програма для аналізу сайту drabivska-gromada.gov.ua на предмет появи нових сторінок.
# При появі нової сторінки програма аналізує її, вибирає з неї саму цінну інформацію і відпраляє її в Телеграм.

import requests
from bs4 import BeautifulSoup
import json
import time as t
import os
from datetime import datetime
import telebot
import configparser
import chardet
from urllib.parse import urlparse, urlunparse

# Завантажуємо конфігураційні дані для авторизації
config = configparser.ConfigParser()
config.read('auth.ini')

# Задаємо основні параметри
SITEMAP_URL = "https://drabivska-gromada.gov.ua/sitemap.xml"
SITEMAP_FILE = "sitemap_local.xml"
PARSER_FILE = "parser.json"
INFORM_LOG_FILE = "inform.log"
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if TELEGRAM_BOT_TOKEN is None:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set. Please check your environment variables.")
CHAT_ID = config.get('telegram', 'CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Визначаємо час початку роботи програми та створюємо файл для логів
start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = f"log_{start_time}.ini"


# Функція для визначення кодування файлу
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
    result = chardet.detect(raw_data)
    return result['encoding']


# Завантаження логів з файлу inform.log, якщо такий існує
def load_inform_log():
    if os.path.exists(INFORM_LOG_FILE):
        encoding = detect_encoding(INFORM_LOG_FILE)
        with open(INFORM_LOG_FILE, 'r', encoding=encoding, errors='ignore') as file:
            urls = set()
            for line in file:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    url = parts[1].strip()
                    normalized = normalize_url(url)
                    urls.add(normalized)
            return urls
    return set()


# Збереження нового URL у файл inform.log
def save_to_inform_log(url):
    normalized_url = normalize_url(url)
    with open(INFORM_LOG_FILE, 'a', encoding='utf-8') as file:
        file.write(str(datetime.now()) + " | " + normalized_url + "\n")


# Завантаження SITEMAP
def download_sitemap():
    response = requests.get(SITEMAP_URL)
    with open(SITEMAP_FILE, 'wb') as file:
        file.write(response.content)


# Парсинг і розбір SITEMAP
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


# Завантаження JSON даних з файлу
def load_json(filename):
    if os.path.exists(filename):
        encoding = detect_encoding(filename)
        with open(filename, 'r', encoding=encoding, errors='ignore') as file:
            try:
                data = json.load(file)
                return data
            except json.JSONDecodeError as e:
                print(f"Error loading JSON from {filename}: {e}")
                return {}
    return {}


# Збереження даних у форматі JSON у файл
def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# Порівняння двох SITEMAP та пошук нових записів
def compare_sitemaps(old, new):
    old_set = {entry['loc'] for entry in old}
    new_set = {entry['loc'] for entry in new}
    return [entry for entry in new if entry['loc'] not in old_set]


def normalize_url(url):
    parsed = urlparse(url)
    # Видаляємо фрагмент (після #) і стандартні порти
    normalized = urlunparse(parsed._replace(fragment='')).rstrip('/')
    return normalized.lower()  # Перетворюємо на нижній регістр для уніфікації


# Отримання даних зі сторінки
def fetch_page_data(url, lastmod):
    response = requests.get(url)

    # Перевіряємо статус відповіді
    if response.status_code == 404:
        print(f"Error 404: {url} not found.")
        return None  # Повертаємо None, якщо сторінка не існує

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


# Збереження HTML сторінки у файл
def save_html_page(url, filename):
    response = requests.get(url)
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(response.text)


# Відправка повідомлення в Telegram
def send_telegram_message(chat_id, message):
    while True:
        try:
            bot.send_message(chat_id, message, parse_mode='Markdown')
            print(f"Message sent to {chat_id}: {message}")  # Додати логування
            break
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Error sending message: {e}")  # Логування помилки
            if e.error_code == 429:
                retry_after = int(e.result_json['parameters']['retry_after'])
                t.sleep(retry_after)
            else:
                break


# Форматування дати у вигляді dd.mm.yyyy
def format_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")


def load_informed_urls():
    if os.path.exists('informed_urls.json'):
        if os.path.getsize('informed_urls.json') > 0:  # Перевіряємо, чи файл не порожній
            with open('informed_urls.json', 'r', encoding='utf-8') as file:
                return set(json.load(file))
    return set()


def save_informed_urls(informed_urls):
    with open('informed_urls.json', 'w', encoding='utf-8') as file:
        json.dump(list(informed_urls), file, ensure_ascii=False, indent=4)



# Головна функція програми
def main():
    if not os.path.exists('pages'):
        os.makedirs('pages')

    informed_urls = load_informed_urls()

    # ... обробка нових записів ...


    # Початкове завантаження та аналіз sitemap
    download_sitemap()
    sitemap_entries = parse_sitemap()

    # Завантаження існуючих записів у JSON
    old_entries = load_json('sitemap.json')

    # Порівняння записів з новими записами
    new_entries = compare_sitemaps(old_entries, sitemap_entries)

    # Збереження всіх записів у JSON
    save_json(sitemap_entries, 'sitemap.json')

    # Моніторинг змін у sitemap
    last_online_check = t.time()
    old_files = set(os.listdir('pages'))

    for entry in new_entries:
        loc = entry['loc']
        normalized_loc = normalize_url(loc)
        if normalized_loc in informed_urls:
            continue

        # ... обробка запису ...

        informed_urls.add(normalized_loc)
        save_informed_urls(informed_urls)

        lastmod = entry['lastmod']

        # Створення нового назви файлу з loc
        filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
        html_filename = os.path.join('pages', filename)

        # Збереження HTML файлу
        save_html_page(loc, html_filename)

        # Отримання даних зі сторінки
        page_data = fetch_page_data(loc, lastmod)

        if page_data:
            # Оновлення файлу parser.json
            parser_data = load_json(PARSER_FILE)
            parser_data[loc] = page_data
            save_json(parser_data, PARSER_FILE)

            # Відправка повідомлення в Telegram
            formatted_date = format_date(page_data['time'])
            message = (f"_{formatted_date}_\n"
                       f"*{page_data['title']}*\n\n"
                       f"{page_data['description']}\n\n"
                       f"{page_data['url']}\n")
            send_telegram_message(CHAT_ID, message)

            # Запис у файл inform.log
            save_to_inform_log(loc)
        else:
            print(f"Could not fetch data for {loc}. Page may not exist.")

    # Перевіряємо наявність нових файлів в директорії pages
    while True:
        current_files = set(os.listdir('pages'))
        new_files = current_files - old_files

        if new_files:
            for file_name in new_files:
                loc = "https://drabivska-gromada.gov.ua/" + file_name.replace("_", "/").replace(".html", "")
                entry = next((e for e in sitemap_entries if e['loc'] == loc), None)
                if entry and loc not in informed_urls:
                    page_data = fetch_page_data(loc, entry['lastmod'])

                    # Оновлення файлу parser.json
                    parser_data = load_json(PARSER_FILE)
                    parser_data[loc] = page_data
                    save_json(parser_data, PARSER_FILE)

                    # Відправка повідомлення в Telegram
                    if page_data:
                        formatted_date = format_date(page_data['time'])
                        message = (f"_{formatted_date}_\n"
                                   f"*{page_data['title']}*\n\n"
                                   f"{page_data['description']}\n\n"
                                   f"{page_data['url']}\n")
                        send_telegram_message(CHAT_ID, message)
                    else:
                        print(f"Could not fetch data for {loc}. Page may not exist.")

                    # Запис логів у файл inform.log
                    save_to_inform_log(loc)

            old_files = current_files

        else:
            # Заводимо таймер на 15хв
            now = t.time()
            if now - last_online_check >= 15 * 60:  # 15 хвилин
                download_sitemap()
                new_sitemap_entries = parse_sitemap()
                new_entries = compare_sitemaps(sitemap_entries, new_sitemap_entries)

                # Шукаємо нові записи
                if new_entries:
                    for entry in new_entries:
                        loc = entry['loc']
                        if loc in informed_urls:
                            continue

                        lastmod = entry['lastmod']
                        page_data = fetch_page_data(loc, lastmod)

                        # Створення назви файлу з loc
                        filename = loc.replace("https://drabivska-gromada.gov.ua/", "").replace("/", "_") + ".html"
                        html_filename = os.path.join('pages', filename)

                        # Збереження HTML файлу
                        save_html_page(loc, html_filename)

                        # Оновлення parser.json
                        parser_data = load_json(PARSER_FILE)
                        parser_data[loc] = page_data
                        save_json(parser_data, PARSER_FILE)

                        # Відправка повідомлення в Telegram
                        if page_data:
                            formatted_date = format_date(page_data['time'])
                            message = (f"_{formatted_date}_\n"
                                       f"*{page_data['title']}*\n\n"
                                       f"{page_data['description']}\n\n"
                                       f"{page_data['url']}\n")
                            send_telegram_message(CHAT_ID, message)
                        else:
                            print(f"Could not fetch data for {loc}. Page may not exist.")

                        # Запис логів у файл inform.log
                        save_to_inform_log(loc)

                    sitemap_entries = new_sitemap_entries
                    old_files = set(os.listdir('pages'))

                last_online_check = t.time()
            else:
                t.sleep(5)

if __name__ == "__main__":
    main()