import json
from datetime import datetime

# Функція для перетворення рядка з файлу inform.log у словник
def parse_log_line(line):
    timestamp_str, url = line.strip().split(" | ")
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
    return {"url": url, "timestamp": timestamp.strftime("%Y-%m-%d")}

# Читання даних з файлу inform.log
with open("inform.log", "r") as log_file:
    log_lines = log_file.readlines()

# Перетворення кожного рядка у словник
data = [parse_log_line(line) for line in log_lines]

# Запис даних у файл inform.json
with open("inform.json", "w") as json_file:
    json.dump(data, json_file, indent=4)

print("Дані успішно перетворено та записано у файл inform.json")
