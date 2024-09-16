import os
from dotenv import load_dotenv

load_dotenv()

# Основні параметри
SITEMAP_URL = "https://drabivska-gromada.gov.ua/sitemap.xml"
SITEMAP_FILE = "sitemap_local.xml"
PARSER_FILE = "parser.json"
NOINFORMED_URLS_FILE = "noinformed_urls.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if TELEGRAM_BOT_TOKEN is None or CHAT_ID is None:
    raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set. Please check your environment variables.")