import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services import search_weapon, download_image, extract_weapon_list

keys = ["ттх", "ттк", "о"]

PERMISSIONS = {
    "ттх": 'ttx', 
    "ттк": 'ttk', 
    "о": 'ttx_2'
    }

async def run(message, args, bot):
    cmd_text = message.text.lower()

    mode = "weapons.php"
    if "ттк" in cmd_text:
        mode = "weapons_ttk.php"

    if not args:
        await message.answer(
            "Укажите название оружия. Пример: <code>ттх deagle</code>",
            parse_mode="HTML",
        )
        return

    await process_weapon(message, args, mode, bot)


async def process_weapon(message_or_callback, weapon_name, mode, bot):
    # Определяем, откуда пришел вызов (сообщение или нажатие кнопки)
    is_callback = hasattr(message_or_callback, "data")
    message = message_or_callback.message if is_callback else message_or_callback

    # Показываем статус "печатает"
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    resp = await search_weapon(weapon_name, mode)

    # 1. Если API вернуло "1" — значит есть картинка
    if resp == "1":
        img_data = await download_image()
        if img_data:
            photo = BufferedInputFile(img_data, filename="result.png")
            # Если это callback, можно отправить новое фото, но проще удалить старое меню и прислать фото
            if is_callback:
                await message.delete()
            await message.answer_photo(photo)
        else:
            await message.answer("Ошибка: Не удалось загрузить фото.")

    # 2. Если "Нет результатов" — пробуем показать кнопки
    elif "Нет результатов" in resp:
        variants = extract_weapon_list(resp)
        if variants and mode == "weapons.php":
            builder = InlineKeyboardBuilder()

            # Добавляем кнопки (максимум 10)
            for w in variants[:10]:
                # В callback_data передаем префикс "wp:" и имя оружия
                # Осторожно с длиной callback_data (макс 64 байта)
                short_name = w[:40]
                builder.button(text=short_name, callback_data=f"wp:{short_name}")

            builder.adjust(1)  # В один столбец

            await message.answer(
                f"{resp}\nВыберите вариант:", reply_markup=builder.as_markup()
            )
        else:
            await message.answer(resp)

    # 3. Просто текст (обычно для ТТК)
    else:
        await message.answer(resp)


# Обработчик кнопки (вызывается из main.py)
async def handle_callback(callback, bot):
    # callback.data выглядит как "wp:Ak-47"
    weapon_name = callback.data.split(":", 1)[1]

    await callback.answer("Генерирую...")
    # Вызываем ту же функцию, но передаем callback
    await process_weapon(callback, weapon_name, "weapons.php", bot)
