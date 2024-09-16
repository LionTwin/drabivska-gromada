import telebot
import time as t
from config import TELEGRAM_BOT_TOKEN

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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