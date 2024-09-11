from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
import asyncio
import logging

# Налаштування журналу
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Вставте ваш токен та ідентифікатор каналу тут
TOKEN = '1993185507:AAGLjPXjJHXdg1dKz8Df8F1w4vZzfP351pk'
# CHANNEL_ID = '-1002165626017'
CHANNEL_ID = '@drabivska_gromada_news'

async def get_channel_id():
    bot = Bot(token=TOKEN)
    chat = await bot.get_chat(CHANNEL_ID)
    print(f"Numeric Channel ID: {chat.id}")
    await bot.session.close()

asyncio.run(get_channel_id())

async def delete_last_message():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        updates = await bot.get_updates(limit=100, allowed_updates=['channel_post'])

        # Виведення всіх отриманих оновлень
        for update in updates:
            logger.info(f"Update: {update}")

        # Фільтрація оновлень для знаходження останнього повідомлення в потрібному каналі
        channel_posts = [update.channel_post for update in updates if
                         update.channel_post and update.channel_post.chat.id == CHANNEL_ID]

        if channel_posts:
            last_message = channel_posts[-1]
            try:
                await bot.delete_message(chat_id=CHANNEL_ID, message_id=last_message.message_id)
                logger.info(f"Deleted message with ID {last_message.message_id} from channel {CHANNEL_ID}")
            except TelegramBadRequest as e:
                if "message to delete not found" in str(e):
                    logger.warning(f"Message with ID {last_message.message_id} was already deleted or not found.")
                else:
                    raise
        else:
            logger.info("No recent messages found in the specified channel.")
    except Exception as e:
        logger.error(f"Failed to delete message: {e}", exc_info=True)
    finally:
        await bot.session.close()


async def start_deleting():
    while True:
        await delete_last_message()
        await asyncio.sleep(5)  # Збільшено інтервал до 5 секунд


if __name__ == '__main__':
    asyncio.run(start_deleting())