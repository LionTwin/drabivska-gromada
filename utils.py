from urllib.parse import urlparse, urlunparse
import json
import os
import requests
from requests.exceptions import RequestException
import logging
import time as t

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment='')).rstrip('/').lower()

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                logging.error(f"Error loading JSON from {filename}: {e}")
                return {}
    return {}

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def fetch_with_retry(url, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt + 1 == max_retries:
                logging.error(f"All attempts failed for {url}")
                raise
            t.sleep(delay)