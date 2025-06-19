# bot/handlers/search.py
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loader import dp
from bot.services.parser import parse_article_text

# Пример: пользователь выбрал статью по инлайн-кнопке
@dp.callback_query_handler(lambda c: c.data.startswith("read_article:"))
async def send_article(callback_query: types.CallbackQuery):
    article_url = callback_query.data.split(":", 1)[1]

    await callback_query.message.edit_text("⏳ Загружаем статью...")

    parsed_text = parse_article_text(article_url)

    if len(parsed_text) > 4096:
        for i in range(0, len(parsed_text), 4096):
            await callback_query.message.answer(parsed_text[i:i+4096])
    else:
        await callback_query.message.answer(parsed_text)
