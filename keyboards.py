from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные статьи Kadrovik.uz", callback_data="kadrovik_latest")],
        [InlineKeyboardButton(text="Рубрики Kadrovik.uz", callback_data="kadrovik_news")],
        [InlineKeyboardButton(text="Поиск по Kadrovik.uz", callback_data="kadrovik_search")],
        [InlineKeyboardButton(text="Помощь", callback_data="help")],
        [InlineKeyboardButton(text="О боте", callback_data="about")],
    ])
    return keyboard