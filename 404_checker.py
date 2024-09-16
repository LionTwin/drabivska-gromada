import json
import requests
from urllib.parse import urlparse, urlunparse


def check_urls(input_file, valid_output, invalid_output):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    valid_urls = []
    invalid_urls = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for item in data:
        url = item.get('url')
        timestamp = item.get('timestamp')

        if not url or not isinstance(url, str):
            print(f"Пропускаємо некоректний URL: {item}")
            continue

        try:
            parsed_url = urlparse(url)
            for scheme in ['https', 'http']:
                current_url = urlunparse(parsed_url._replace(scheme=scheme))
                response = requests.get(current_url, headers=headers, timeout=10, allow_redirects=True)

                if response.status_code == 200:
                    valid_urls.append(item)
                    print(f"Valid URL: {url}")
                    break
                elif response.status_code == 404:
                    invalid_urls.append(item)
                    print(f"Invalid URL (404): {url}")
                    break
            else:
                invalid_urls.append(item)
                print(f"Invalid URL (Status code: {response.status_code}): {url}")

        except requests.RequestException as e:
            invalid_urls.append(item)
            print(f"Error checking URL: {url}. Error: {str(e)}")

    with open(valid_output, 'w', encoding='utf-8') as f:
        json.dump(valid_urls, f, indent=2, ensure_ascii=False)

    with open(invalid_output, 'w', encoding='utf-8') as f:
        json.dump(invalid_urls, f, indent=2, ensure_ascii=False)

    print(f"\nValid URLs: {len(valid_urls)}")
    print(f"Invalid URLs: {len(invalid_urls)}")


# Використання функції
check_urls('urls.json', 'informed_urls.json', 'noinformed_urls.json')