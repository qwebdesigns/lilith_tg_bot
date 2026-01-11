import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services import get_text

keys = ["карты"]

PERMISSIONS = {
    "карты": 'maps'
    }

def get_maps_keyboard():
    # Создаем кнопку с callback_data="refresh_maps"
    button = InlineKeyboardButton(text="Обновить 🔄", callback_data="refresh_maps")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def run(message, args, bot):
    text = await get_text("maps.php")
    await message.answer(text, reply_markup=get_maps_keyboard())


# Функция для обновления (вызывается из main.py при нажатии кнопки)
async def handle_callback(callback, bot):
    text = await get_text("maps.php")

    # Показываем уведомление "всплывашка"
    await callback.answer("Обновлено ✅")

    try:
        # Редактируем сообщение
        await callback.message.edit_text(text, reply_markup=get_maps_keyboard())
    except Exception:
        # Если текст не изменился, телеграм может выдать ошибку, игнорируем
        pass
