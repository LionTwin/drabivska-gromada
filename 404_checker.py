import requests
import json

# Завантаження даних з файлу informed_urls.json
with open('informed_urls.json', 'r') as file:
    data = json.load(file)

def check_url(url):
    try:
        response = requests.get(url)
        return response.status_code == 404
    except requests.RequestException:
        return False

# Обробка URL
for item in data:
    url = item['url']
    is_error = check_url(url)
    if is_error:
        print(f"URL {url} призвів до помилки 404")
        # Записуємо крок у файл noinformed_urls.json
        with open('noinformed_urls.json', 'a') as noinformed_file:
            json.dump({'url': url, 'error': 404}, noinformed_file)
            noinformed_file.write('\n')

# Видалення помилкових URL зі списку
data = [item for item in data if not check_url(item['url'])]

# Запис оновленого списку в файл
with open('informed_urls.json', 'w') as outfile:
    json.dump(data, outfile, indent=4)
