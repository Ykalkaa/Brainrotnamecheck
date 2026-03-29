import asyncio
import logging
import os
from openai import AsyncOpenAI
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

PROMPT = (
    "Ты — анализатор персонажей из игры Roblox Brainrot. "
    "На скриншоте найди ТОЛЬКО персонажей у которых видно имя и прибыль (M/s, B/s, T/s). "
    "Для каждого персонажа выведи ОДНУ строку в формате: "
    "[эмодзи рейтинга] [Название персонажа] [прибыль] [мутация если есть] [эмодзи]. "
    "Например: ✨ La Grande Combinasion 100M/s Divine 💫👑 "
    "Выводи только то что реально видно на экране. Без лишних слов."
)

@dp.message(F.photo)
async def handle_photo(message: Message):
    status_msg = await message.answer("Считываю брейнрот... 🛠️")
    try:
        photo_id = message.photo[-1].file_id
        file = await bot.get_file(photo_id)
        photo_bytes = await bot.download_file(file.file_path)
        image_data = base64.b64encode(photo_bytes.read()).decode("utf-8")

        response = await client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ]
        )

        await status_msg.delete()
        result = response.choices[0].message.content
        if result:
            await message.answer(result)
        else:
            await message.answer("Нейронка вернула пустой ответ. Попробуй другой ракурс! 🤔")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text(f"Ошибка: {e}")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Здарова! Кидай скриншот с персонажами Roblox! 👾")

async def main():
    print("=== БОТ ЗАПУЩЕН И ЖДЕТ КАРТИНКИ ===")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
