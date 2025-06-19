from aiogram import Router, types

router = Router()

@router.callback_query(lambda c: c.data == "settings")
async def settings_handler(callback_query: types.CallbackQuery):
    await callback_query.message.answer("⚙️ Настройки (язык, очистка истории и т.д.)")
