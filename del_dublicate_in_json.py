import json

def remove_duplicates(data):
    # Створюємо словник, використовуючи url як ключі
    url_dict = {item['url']: item for item in data}

    # Отримуємо список унікальних значень
    unique_data = list(url_dict.values())
    return unique_data

# Завантаження даних з файлу informed_urls.json
with open('informed_urls.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Видалення дублікатів
unique_data = remove_duplicates(data)

# Збереження оновленого JSON файлу
with open('informed_urls_unique.json', 'w', encoding='utf-8') as file:
    json.dump(unique_data, file, ensure_ascii=False, indent=4)

print("Дублікати видалено. Оновлений файл збережено як 'informed_urls_unique.json'.")
