import asyncio
import os
import re
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
import yt_dlp

import os
TOKEN = os.environ["BOT_TOKEN"]

bot = Bot(token=TOKEN)
dp = Dispatcher()


class Download(StatesGroup):
    waiting_url = State()
    waiting_quality = State()


menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎬  Скачать видео", callback_data="m:video")],
    [InlineKeyboardButton(text="ℹ️  Помощь", callback_data="m:help")],
])

quality = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔥 1080p", callback_data="q:1080"),
        InlineKeyboardButton(text="👍 720p", callback_data="q:720"),
    ],
    [
        InlineKeyboardButton(text="📉 480p", callback_data="q:480"),
        InlineKeyboardButton(text="🪶 360p", callback_data="q:360"),
    ],
])

WELCOME = (
    "👋 <b>Привет! Я скачиваю видео по ссылке.</b>\n\n"
    "📡 <b>Поддерживаю:</b>\n"
    "🎬  YouTube\n"
    "🎵  TikTok\n"
    "📺  VK Видео\n"
    "📸  Instagram\n"
    "🐦  X (Twitter)\n"
    "👤  Facebook\n"
    "🎮  Twitch\n"
    "🎥  Dailymotion\n"
    "🎬  Vimeo\n"
    "📕  Reddit\n"
    "📌  Pinterest\n"
    "📹  Rutube\n"
    "🎵  Bilibili\n"
    "📱  Snapchat\n"
    "📺  OK.ru\n"
    "🎬  9GAG\n"
    "🎬  Mixkit\n"
    "📷  Pexels\n"
    "🎬  Pixabay\n"
    "…и ещё 1000+ сайтов\n\n"
    "Что делаем?"
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(WELCOME, reply_markup=menu, parse_mode="HTML")


@dp.callback_query(F.data == "m:help")
async def help_cb(q: CallbackQuery):
    await q.message.answer(
        "ℹ️ <b>Как пользоваться</b>\n\n"
        "1️⃣ Нажми «🎬 Скачать видео»\n"
        "2️⃣ Пришли ссылку\n"
        "3️⃣ Выбери качество\n"
        "4️⃣ Жди — файл прилетит\n\n"
        "⚠️ Лимит Telegram: 50 МБ",
        parse_mode="HTML",
    )
    await q.answer()


@dp.callback_query(F.data == "m:video")
async def pick_video(q: CallbackQuery, state: FSMContext):
    await state.set_state(Download.waiting_url)
    await q.message.answer("🎬 Пришли ссылку на видео 👇")
    await q.answer()


@dp.message(F.text)
async def on_text(message: Message, state: FSMContext):
    current = await state.get_state()

    if current == Download.waiting_url.state:
        m = re.search(r"https?://\S+", message.text)
        if not m:
            await message.answer("🤔 Не вижу ссылку. Пришли с http:// или https://")
            return
        await state.update_data(url=m.group(0))
        await state.set_state(Download.waiting_quality)
        await message.answer("🎬 Выбери качество:", reply_markup=quality)

    elif current == Download.waiting_quality.state:
        await message.answer("👆 Нажми кнопку качества выше")

    else:
        m = re.search(r"https?://\S+", message.text)
        if m:
            await state.update_data(url=m.group(0))
            await state.set_state(Download.waiting_quality)
            await message.answer("🎬 Выбери качество:", reply_markup=quality)
        else:
            await message.answer(WELCOME, reply_markup=menu, parse_mode="HTML")


@dp.callback_query(F.data.startswith("q:"))
async def on_quality(q: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get("url")
    height = q.data.split(":")[1]
    await state.clear()
    await q.answer()
    if not url:
        await q.message.answer("❌ Ссылка потеряна. Напиши /start заново.")
        return
    await _download(q.message, url, height)


async def _download(message, url, height):
    status = await message.answer(f"⏳ Скачиваю в {height}p…")
    tmp = tempfile.mkdtemp()

    opts = {
        "outtmpl": os.path.join(tmp, "%(title).50s.%(ext)s"),
        "format": f"best[height<={height}][ext=mp4]/best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
    }

    try:
        def _dl():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await asyncio.to_thread(_dl)
        title = info.get("title", "Media")

        files = os.listdir(tmp)
        if not files:
            raise RuntimeError("Файл не найден")

        path = os.path.join(tmp, files[0])

        if os.path.getsize(path) > 49 * 1024 * 1024:
            await status.edit_text("❌ Файл > 50 МБ. Попробуй ниже качество.")
            return

        await status.edit_text("📤 Отправляю…")
        f = FSInputFile(path)

        caption = '<a href="https://t.me/Napominalkaa1_bot">📥 Скачать ещё → @Napominalkaa1_bot</a>'
        await message.answer_video(
            f,
            caption=caption,
            supports_streaming=True,
            parse_mode="HTML",
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ {str(e)[:500]}")
    finally:
        try:
            for fn in os.listdir(tmp):
                os.remove(os.path.join(tmp, fn))
            os.rmdir(tmp)
        except OSError:
            pass


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
