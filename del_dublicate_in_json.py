import json

# Завантаження JSON файлу
with open('your_file.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Видалення дублікатів
unique_data = list(set(data))

# Збереження оновленого JSON файлу
with open('your_file_unique.json', 'w', encoding='utf-8') as file:
    json.dump(unique_data, file, ensure_ascii=False, indent=4)

print("Дублікати видалено. Оновлений файл збережено як 'your_file_unique.json'.")
