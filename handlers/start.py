from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

@router.message(commands=["start"])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск статьи", callback_data="search")],
        [InlineKeyboardButton(text="📰 Актуальное Kadrovik.uz", callback_data="news")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])
    await message.answer("Добро пожаловать! Выберите опцию:", reply_markup=keyboard)
