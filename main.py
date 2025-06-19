import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import json
from datetime import datetime
from io import BytesIO

# Импорт парсеров
from utils.parser import get_latest_articles, search_articles, fetch_article_content
from utils.parsing_rubriki import fetch_rubrika_articles, RUBRIKI

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Константы
MAX_ARTICLES = 5  # Максимальное количество статей для отображения
MAX_MESSAGE_LENGTH = 4000  # Максимальная длина сообщения в Telegram

# Менеджер пользователей
class UserManager:
    def __init__(self):
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                self.users = json.load(f)

    def save_users(self):
        with open("users.json", "w") as f:
            json.dump(self.users, f, indent=4)

    def add_user(self, user_id, name, phone):
        self.users[user_id] = {"name": name, "phone": phone}
        self.save_users()

    def get_user(self, user_id):
        return self.users.get(user_id)

user_manager = UserManager()

# Состояния FSM
class AuthStates(StatesGroup):
    WAITING_FOR_NAME = State()
    WAITING_FOR_PHONE = State()

class SearchStates(StatesGroup):
    WAITING_FOR_QUERY = State()

class RubrikaStates(StatesGroup):
    WAITING_FOR_RUBRIKA = State()
    WAITING_FOR_ARTICLE = State()

# Глобальные переменные
latest_articles = []

# --- Клавиатуры ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Актуальные статьи",
            callback_data="kadrovik_latest"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="Рубрики",
            callback_data="kadrovik_news"
        ),
        types.InlineKeyboardButton(
            text="Поиск",
            callback_data="kadrovik_search"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="Помощь",
            callback_data="help"
        ),
        types.InlineKeyboardButton(
            text="О боте",
            callback_data="about"
        )
    )
    return builder.as_markup()

# --- Обработчики команд ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user = user_manager.get_user(user_id)
    
    if user:
        await message.answer(
            f"Добро пожаловать обратно, {user['name']}!",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer("Добро пожаловать! Пожалуйста, введите ваше имя:")
        await state.set_state(AuthStates.WAITING_FOR_NAME)

@dp.message(AuthStates.WAITING_FOR_NAME)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь введите ваш номер телефона:")
    await state.set_state(AuthStates.WAITING_FOR_PHONE)

@dp.message(AuthStates.WAITING_FOR_PHONE)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    data = await state.get_data()
    user_manager.add_user(user_id, data['name'], message.text)
    await message.answer(
        f"Регистрация завершена, {data['name']}!",
        reply_markup=get_main_menu()
    )
    await state.clear()

# --- Основные обработчики ---
async def send_article_content(chat_id: int, article: dict):
    """Отправляет содержимое статьи с обработкой длинных текстов"""
    try:
        content = await fetch_article_content(article['url'])
        if not content:
            await bot.send_message(chat_id, "Не удалось загрузить содержимое статьи")
            return

        header = f"📰 {article['title']}\n📅 {article['date']}\n\n"
        full_content = header + content

        if len(full_content) > MAX_MESSAGE_LENGTH:
            # Отправляем файлом если текст слишком длинный
            file = BytesIO(full_content.encode('utf-8'))
            file.name = f"{article['title'][:50]}.txt"
            await bot.send_document(chat_id, file)
        else:
            await bot.send_message(chat_id, full_content)
    except Exception as e:
        logger.error(f"Ошибка при отправке статьи: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при обработке статьи")

# --- Обработчики callback ---
@dp.callback_query(lambda c: c.data == "kadrovik_latest")
async def handle_latest_articles(callback: types.CallbackQuery):
    global latest_articles
    latest_articles = await get_latest_articles("ru")  # Явно указываем язык
    
    if not latest_articles:
        await callback.message.answer("Не удалось загрузить последние статьи")
        return

    builder = InlineKeyboardBuilder()
    for i in range(min(len(latest_articles), MAX_ARTICLES)):
        builder.add(types.InlineKeyboardButton(
            text=f"Статья {i+1}",
            callback_data=f"article_{i}"
        ))
    builder.adjust(2)

    articles_list = "\n".join(
        f"{i+1}. {art['title']}" 
        for i, art in enumerate(latest_articles[:MAX_ARTICLES])
    )
    await callback.message.answer(
        f"📰 Последние статьи:\n\n{articles_list}",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("article_"))
async def handle_article(callback: types.CallbackQuery):
    try:
        idx = int(callback.data.split("_")[1])
        if 0 <= idx < len(latest_articles):
            await send_article_content(callback.from_user.id, latest_articles[idx])
        else:
            await callback.message.answer("Статья не найдена")
    except (IndexError, ValueError):
        await callback.message.answer("Ошибка: неверный идентификатор статьи")

@dp.callback_query(lambda c: c.data == "kadrovik_search")
async def handle_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите поисковый запрос:")
    await state.set_state(SearchStates.WAITING_FOR_QUERY)

@dp.callback_query(lambda c: c.data == "kadrovik_news")
async def handle_rubriki(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    
    # Создаем кнопки для рубрик с безопасными callback_data
    rubrika_ids = {name: f"rub_{hash(name) % 1000:03d}" for name in RUBRIKI}
    await state.update_data(rubrika_ids=rubrika_ids)
    
    for name, rub_id in rubrika_ids.items():
        builder.add(types.InlineKeyboardButton(
            text=name,
            callback_data=rub_id
        ))
    
    builder.add(types.InlineKeyboardButton(
        text="Калькулятор отпускных",
        url="https://kadrovik.uz/publish/doc/text199228_kalkulyator_otpusknyh"
    ))
    
    builder.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="main_menu"
    ))
    
    builder.adjust(1)
    await callback.message.answer(
        "Выберите рубрику:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RubrikaStates.WAITING_FOR_RUBRIKA)

@dp.callback_query(RubrikaStates.WAITING_FOR_RUBRIKA)
async def handle_rubrika_select(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "main_menu":  # Обработка кнопки "Назад"
        await handle_main_menu(callback, state)
        return
    
    data = await state.get_data()
    rubrika_ids = data.get("rubrika_ids", {})
    
    # Находим название рубрики по ID
    rubrika_name = next((name for name, rub_id in rubrika_ids.items() 
                        if rub_id == callback.data), None)
    
    if not rubrika_name or rubrika_name not in RUBRIKI:
        await callback.message.answer("Рубрика не найдена")
        return
    
    articles = await fetch_rubrika_articles(RUBRIKI[rubrika_name])
    if not articles:
        await callback.message.answer("В этой рубрике пока нет статей")
        return
    
    # Сохраняем статьи в состоянии
    await state.update_data(current_articles=articles)
    
    builder = InlineKeyboardBuilder()
    for i in range(min(len(articles), MAX_ARTICLES)):
        builder.add(types.InlineKeyboardButton(
            text=f"Статья {i+1}",
            callback_data=f"rub_art_{i}"
        ))
    
    builder.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="kadrovik_news"  # Изменено для возврата в меню рубрик
    ))
    builder.adjust(2)
    
    articles_list = "\n".join(
        f"{i+1}. {art['title']}" 
        for i, art in enumerate(articles[:MAX_ARTICLES])
    )
    await callback.message.answer(
        f"📚 Рубрика: {rubrika_name}\n\n{articles_list}",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RubrikaStates.WAITING_FOR_ARTICLE)

@dp.callback_query(RubrikaStates.WAITING_FOR_ARTICLE)
async def handle_rubrika_article(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "kadrovik_news":  # Обработка кнопки "Назад"
        await handle_rubriki(callback, state)
        return
    
    try:
        data = await state.get_data()
        articles = data.get("current_articles", [])
        
        if callback.data.startswith("rub_art_"):
            idx = int(callback.data.split("_")[2])
            if 0 <= idx < len(articles):
                await send_article_content(callback.from_user.id, articles[idx])
            else:
                await callback.message.answer("Статья не найдена")
    except Exception as e:
        logger.error(f"Ошибка обработки статьи из рубрики: {e}")
        await callback.message.answer("Произошла ошибка при загрузке статьи")

@dp.callback_query(lambda c: c.data == "kadrovik_news")
async def handle_rubriki(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    
    # Создаем кнопки для рубрик с безопасными callback_data
    rubrika_ids = {name: f"rub_{hash(name) % 1000:03d}" for name in RUBRIKI}
    await state.update_data(rubrika_ids=rubrika_ids)
    
    for name, rub_id in rubrika_ids.items():
        builder.add(types.InlineKeyboardButton(
            text=name,
            callback_data=rub_id
        ))
    
    builder.add(types.InlineKeyboardButton(
        text="Калькулятор отпускных",
        url="https://kadrovik.uz/publish/doc/text199228_kalkulyator_otpusknyh"
    ))
    
    builder.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="main_menu"  # Возврат в главное меню
    ))
    
    builder.adjust(1)
    await callback.message.answer(
        "Выберите рубрику:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RubrikaStates.WAITING_FOR_RUBRIKA)

@dp.callback_query(RubrikaStates.WAITING_FOR_ARTICLE)
async def handle_rubrika_article(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "kadrovik_news":
        await handle_rubriki(callback, state)
        return
    
    try:
        data = await state.get_data()
        articles = data.get("current_articles", [])
        
        if callback.data.startswith("rub_art_"):
            idx = int(callback.data.split("_")[2])
            if 0 <= idx < len(articles):
                await send_article_content(callback.from_user.id, articles[idx])
            else:
                await callback.message.answer("Статья не найдена")
    except Exception as e:
        logger.error(f"Ошибка обработки статьи из рубрики: {e}")
        await callback.message.answer("Произошла ошибка при загрузке статьи")

@dp.callback_query(lambda c: c.data == "help")
async def handle_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "ℹ️ Помощь:\n\n"
        "• Используйте кнопки меню для навигации\n"
        "• Для поиска статей нажмите 'Поиск'\n"
        "• Выберите рубрику для просмотра тематических статей"
    )

@dp.callback_query(lambda c: c.data == "about")
async def handle_about(callback: types.CallbackQuery):
    await callback.message.answer(
        "🤖 О боте:\n\n"
        "Этот бот помогает работать с материалами сайта Kadrovik.uz\n"
        "Версия: 1.0\n"
        "Разработчик: Ваша компания"
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu()
    )

# Обработчик поиска
@dp.message(SearchStates.WAITING_FOR_QUERY)
async def process_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите непустой запрос")
        return
    
    articles = await search_articles(query, "ru")
    if not articles:
        await message.answer("По вашему запросу ничего не найдено")
        await state.clear()
        return
    
    # Сохраняем результаты поиска
    await state.update_data(search_results=articles)
    
    builder = InlineKeyboardBuilder()
    for i in range(min(len(articles), MAX_ARTICLES)):
        builder.add(types.InlineKeyboardButton(
            text=f"Статья {i+1}",
            callback_data=f"search_art_{i}"
        ))
    builder.adjust(2)
    
    articles_list = "\n".join(
        f"{i+1}. {art['title']}" 
        for i, art in enumerate(articles[:MAX_ARTICLES])
    )
    await message.answer(
        f"🔍 Результаты поиска по запросу '{query}':\n\n{articles_list}",
        reply_markup=builder.as_markup()
    )
    await state.clear()

# Проверка авторизации для всех сообщений
@dp.message()
async def check_auth(message: types.Message):
    if not user_manager.get_user(str(message.from_user.id)):
        await message.answer("Пожалуйста, зарегистрируйтесь через /start")

# Запуск бота
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())