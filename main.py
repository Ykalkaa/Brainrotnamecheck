import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from openai import AsyncOpenAI
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

OPENROUTER_KEYS = [
    k for k in [
        os.environ.get("OPENROUTER_KEY_1"),
        os.environ.get("OPENROUTER_KEY_2"),
        os.environ.get("OPENROUTER_KEY_3"),
    ] if k
]

current_key_index = 0

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

PROMPT = (
    "You are analyzing a Roblox Brainrot game screenshot. "
    "Find ALL characters that have a visible name tag above them. "
    "If no characters found write only: Персонажей не найдено 🤷\n\n"
    "For each character output EXACTLY ONE line:\n"
    "[mutation emoji] [Character Name] [income] [Mutation name if exists] [1-2 emojis matching appearance]\n\n"
    "INCOME RULES:\n"
    "- Income is YELLOW text near the name: $162.5M/s, $5B, $550M/s etc\n"
    "- NEVER use GREEN text - that is Collect/offline cash, ignore it\n"
    "- If income not visible write ❓\n\n"
    "MUTATION RULES (word shown ABOVE character name):\n"
    "- Rainbow = 🌈 and write 'Rainbow' in text\n"
    "- Divine = ✨ and write 'Divine' in text\n"
    "- Diamond = 💎 and write 'Diamond' in text\n"
    "- Radioactive = ☢️ and write 'Radioactive' in text\n"
    "- Gold = 🥇 and write 'Gold' in text\n"
    "- Cursed = 👿 and write 'Cursed' in text\n"
    "- Frozen = ❄️ and write 'Frozen' in text\n"
    "- Burning = 🔥 and write 'Burning' in text\n"
    "- Shiny = ⭐ and write 'Shiny' in text\n"
    "- No mutation = ✨ write nothing\n"
    "NEVER write: Secret, Common, Rare, Epic - those are rarity not mutation!\n\n"
    "APPEARANCE EMOJIS: pick 1-2 based on what the character looks like:\n"
    "snake=🐍, clock=🕐, food=🍕, robot=🤖, fire=🔥, ice=❄️, plant=🌿, "
    "skull=💀, music=🎵, crown=👑, heart=💗, star=⭐, alien=👽 etc\n\n"
    "Copy character NAME exactly as shown on screen, do not fix spelling!\n\n"
    "Example output:\n"
    "🌈 Mariachi Corazoni $162.5M/s Rainbow 🎵👑\n"
    "☢️ Chicleteira Noelteira $127M/s Radioactive 🟢\n"
    "✨ La Grande Combinasion $100M/s Divine 👑\n\n"
    "Output ONLY the character lines, nothing else."
)

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), PingHandler)
    server.serve_forever()

@dp.message(F.photo)
async def handle_photo(message: Message):
    global current_key_index
    status_msg = await message.answer("Считываю брейнрот... 🛠️")
    try:
        photo_id = message.photo[-1].file_id
        file = await bot.get_file(photo_id)
        photo_bytes = await bot.download_file(file.file_path)
        image_data = base64.b64encode(photo_bytes.read()).decode("utf-8")

        for attempt in range(len(OPENROUTER_KEYS) * 3):
            try:
                client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_KEYS[current_key_index]
                )
                response = await asyncio.wait_for(
                    client.chat.completions.create(
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
                    ),
                    timeout=60
                )
                break
            except Exception as e:
                if "429" in str(e):
                    logging.warning(f"Ключ {current_key_index+1} исчерпан, переключаю...")
                    current_key_index = (current_key_index + 1) % len(OPENROUTER_KEYS)
                    if attempt >= len(OPENROUTER_KEYS) - 1:
                        await status_msg.edit_text("❌ Все ключи исчерпаны на сегодня. Попробуй завтра!")
                        return
                    continue
                elif "404" in str(e):
                    logging.warning(f"404 от провайдера, повтор {attempt+1}...")
                    await asyncio.sleep(2)
                    continue
                raise e

        await status_msg.delete()
        result = response.choices[0].message.content
        if result:
            await message.answer(result)
        else:
            await message.answer("Персонажей не найдено 🤷")

    except asyncio.TimeoutError:
        await status_msg.edit_text("⏱️ Нейронка не ответила за 60 сек. Попробуй ещё раз!")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text(f"Ошибка: {e}")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Здарова! Кидай скриншот с персонажами Roblox! 👾")

async def main():
    threading.Thread(target=run_server, daemon=True).start()
    print("=== БОТ ЗАПУЩЕН И ЖДЕТ КАРТИНКИ ===")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
