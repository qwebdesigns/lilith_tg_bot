import json
import os
import random
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

keys = ["раздача", "итоги"]

# НАСТРОЙКА ПРАВ
# Укажи здесь право, которое должно быть у человека в api_users_json.php
# Например: "giveaway" или "admin"
PERMISSIONS = {"раздача": "giveaway", "итоги": "giveaway"}

DB_FILE = "giveawaysTG.json"
db_lock = asyncio.Lock()

# --- РАБОТА С БАЗОЙ ---


def _load_db_sync():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _save_db_sync(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


async def get_db():
    async with db_lock:
        return _load_db_sync()


async def save_giveaway(chat_id, data):
    """Сохраняет данные раздачи для конкретного чата"""
    async with db_lock:
        db = _load_db_sync()
        db[str(chat_id)] = data
        _save_db_sync(db)


async def add_participant(chat_id, user_id, user_name):
    """Добавляет участника"""
    async with db_lock:
        db = _load_db_sync()
        s_chat_id = str(chat_id)
        if s_chat_id in db:
            # Используем словарь, чтобы избежать дублей (id -> name)
            db[s_chat_id]["participants"][str(user_id)] = user_name
            _save_db_sync(db)
            return True
        return False


async def delete_giveaway(chat_id):
    """Удаляет раздачу"""
    async with db_lock:
        db = _load_db_sync()
        if str(chat_id) in db:
            del db[str(chat_id)]
            _save_db_sync(db)


# --- КОМАНДЫ ---


async def run(message, args, bot):
    text = message.text.lower()
    chat_id = message.chat.id

    # 1. ЗАПУСК РАЗДАЧИ
    # Формат: л раздача 5 Золотой АК-47
    if "раздача" in text:
        if not args:
            await message.answer(
                "⚠️ Формат: <code>л раздача [кол-во] [приз]</code>", parse_mode="HTML"
            )
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "⚠️ Вы не указали приз! Пример: <code>л раздача 1 Слона</code>",
                parse_mode="HTML",
            )
            return

        count_str = parts[0]
        prize = parts[1]

        if not count_str.isdigit():
            await message.answer("⚠️ Количество победителей должно быть числом.")
            return

        count = int(count_str)
        if count < 1:
            await message.answer("⚠️ Минимум 1 победитель.")
            return

        # Формируем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text="🎉 Участвую!", callback_data="gw:join")

        msg_text = (
            f"🎁 <b>РАЗДАЧА!</b>\n\n"
            f"Разыгрываем: <b>{prize}</b>\n"
            f"Победителей: <b>{count}</b>\n\n"
            f"👇 Жми кнопку, чтобы попытать удачу!"
        )

        sent_msg = await message.answer(
            msg_text, reply_markup=builder.as_markup(), parse_mode="HTML"
        )

        # Сохраняем в базу
        gw_data = {
            "message_id": sent_msg.message_id,
            "prize": prize,
            "count": count,
            "participants": {},  # id: name
        }
        await save_giveaway(chat_id, gw_data)
        return

    # 2. ИТОГИ РАЗДАЧИ
    if "итоги" in text:
        db = await get_db()
        gw = db.get(str(chat_id))

        if not gw:
            await message.answer("В этом чате нет активной раздачи.")
            return

        participants = gw["participants"]  # dict {id: name}
        user_ids = list(participants.keys())
        count = gw["count"]
        prize = gw["prize"]
        msg_id = gw["message_id"]

        header = f"🎉 <b>Итоги раздачи:</b> {prize}\n\n"

        if not user_ids:
            result_text = header + "😔 Никто не участвовал..."
        else:
            # Выбираем победителей
            winners_count = min(len(user_ids), count)
            winner_ids = random.sample(user_ids, winners_count)

            winners_list = []
            for uid in winner_ids:
                name = participants[uid]
                # Ссылка на профиль
                winners_list.append(f"👤 <a href='tg://user?id={uid}'>{name}</a>")

            result_text = (
                header
                + "🏆 <b>Победители:</b>\n"
                + "\n".join(winners_list)
                + "\n\nПоздравляем! Напишите админу для получения приза."
            )

        # 1. Отправляем итоги
        await message.answer(result_text, parse_mode="HTML")

        # 2. Пытаемся убрать кнопку у старого сообщения
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=msg_id, reply_markup=None
            )
            # Опционально: можно изменить текст старого сообщения, написав "ЗАВЕРШЕНО"
            # await bot.edit_message_text(..., chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass  # Сообщение могли удалить

        # 3. Удаляем из базы
        await delete_giveaway(chat_id)


# --- ОБРАБОТЧИК КНОПОК ---


async def handle_callback(callback: CallbackQuery, bot):
    # callback.data == "gw:join"
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name  # Или html.escape(...) если нужно

    # Добавляем в базу
    # Функция add_participant сама проверит наличие раздачи и вернет True/False
    # (True = добавили, False = раздачи нет или ошибка, но дубли мы обрабатываем перезаписью)

    # Сначала проверим, есть ли раздача вообще
    db = await get_db()
    if str(chat_id) not in db:
        await callback.answer("Эта раздача уже завершена 🛑", show_alert=True)
        return

    # Проверяем, участвует ли уже
    participants = db[str(chat_id)]["participants"]
    if str(user_id) in participants:
        await callback.answer("Ты уже участвуешь! 😎", show_alert=False)
        return

    # Добавляем
    await add_participant(chat_id, user_id, user_name)
    await callback.answer("Ты в деле! Удачи! 🍀", show_alert=False)
