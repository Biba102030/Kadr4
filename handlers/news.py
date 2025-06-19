from aiogram import Router, types

router = Router()

@router.callback_query(lambda c: c.data == "news")
async def news_handler(callback_query: types.CallbackQuery):
    await callback_query.message.answer("📰 Здесь будут актуальные статьи (парсинг).")
