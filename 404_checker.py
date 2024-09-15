import requests
import json

def check_url(url):
    try:
        response = requests.get(url)
        return response.status_code == 404
    except requests.RequestException:
        return False

# Завантаження даних з файлу informed_urls.json
with open('informed_urls.json', 'r') as file:
    data = json.load(file)

# Обробка URL
for item in data:
    url = item['url']
    is_error = check_url(url)
    if is_error:
        print(f"URL {url} призвів до помилки 404")
        # Додавання помилкового URL до списку
        error_entry = {'url': url, 'timestamp': item['timestamp']}
        with open('noinformed_urls.json', 'a') as noinformed_file:
            json.dump(error_entry, noinformed_file)
            noinformed_file.write('\n')

# Видалення помилкових URL зі списку
data = [item for item in data if not check_url(item['url'])]

# Запис оновленого списку в файл
with open('informed_urls.json', 'w') as outfile:
    json.dump(data, outfile, indent=4)
