import json
import os
import time
import html
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Добавили "развод" в ключи
keys = ["предложение", "браки", "развод"]

# НАСТРОЙКА ПРАВ
PERMISSIONS = {"предложение": None, "браки": None, "развод": None}

DB_FILE = "marriages.json"
db_lock = asyncio.Lock()

# --- РАБОТА С БАЗОЙ (АСИНХРОННО И БЕЗОПАСНО) ---


def _load_db_sync():
    """Внутренняя синхронная функция чтения"""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_db_sync(data):
    """Внутренняя синхронная функция записи"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


async def add_record(record):
    """Безопасное добавление записи с блокировкой"""
    async with db_lock:
        db = _load_db_sync()
        db.append(record)
        _save_db_sync(db)


# НОВАЯ ФУНКЦИЯ: Для удаления нам нужно перезаписать базу целиком
async def overwrite_db(new_data):
    """Безопасная перезапись базы (для удаления)"""
    async with db_lock:
        _save_db_sync(new_data)


async def get_db():
    """Безопасное чтение"""
    async with db_lock:
        return _load_db_sync()


def format_duration(start_ts):
    diff = int(time.time() - start_ts)
    days = diff // 86400
    if days > 0:
        return f"{days} дн."
    minutes = diff // 60
    return f"{minutes} мин."


# --- ОСНОВНАЯ КОМАНДА (RUN) ---


async def run(message, args, bot):
    text = message.text.lower()

    # 1. СПИСОК БРАКОВ
    if "браки" in text:
        db = await get_db()
        if not db:
            await message.answer("В этом чате пока нет ни одного союза 🤷‍♂️")
            return

        marriages = []
        friendzones = []

        for record in db:
            duration = format_duration(record["date"])
            u1 = html.escape(record["name1"])
            u2 = html.escape(record["name2"])

            if record["type"] == "marriage":
                line = f"❤️ <b>{u1} + {u2}</b> — уже {duration} вместе!"
                marriages.append(line)
            elif record["type"] == "friendzone":
                line = f"🤡 <b>{u2}</b> френдзонит <b>{u1}</b> — уже {duration}..."
                friendzones.append(line)

        msg_lines = []
        if marriages:
            msg_lines.append("<b>💘 Крепкие браки:</b>")
            msg_lines.extend(marriages)
            msg_lines.append("")

        if friendzones:
            msg_lines.append("<b>🚧 Френдзона:</b>")
            msg_lines.extend(friendzones)

        if not msg_lines:
            await message.answer("Список пуст.")
        else:
            full_text = "\n".join(msg_lines)
            if len(full_text) > 4000:
                await message.answer(full_text[:4000], parse_mode="HTML")
                await message.answer(full_text[4000:], parse_mode="HTML")
            else:
                await message.answer(full_text, parse_mode="HTML")
        return

    # 2. РАЗВОД (НОВОЕ)
    if "развод" in text:
        user_id = message.from_user.id
        db = await get_db()

        found_record = None
        new_db = []

        # Ищем запись, где участвует пользователь
        for rec in db:
            if rec["id1"] == user_id or rec["id2"] == user_id:
                found_record = rec
                # Эту запись мы НЕ добавляем в новый список (удаляем)
            else:
                new_db.append(rec)

        if not found_record:
            await message.answer("Вы свободны как ветер! (Вы ни на ком не женаты) 🤷‍♂️")
            return

        # Сохраняем обновленный список без этого брака
        await overwrite_db(new_db)

        # Вычисляем имя партнера для сообщения
        partner_name = (
            found_record["name2"]
            if found_record["id1"] == user_id
            else found_record["name1"]
        )

        if found_record["type"] == "marriage":
            await message.answer(
                f"💔 <b>{message.from_user.full_name}</b> подал(а) на развод.\n"
                f"Брак с <b>{partner_name}</b> расторгнут. Любовь прошла, завяли помидоры...",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🤡 <b>{message.from_user.full_name}</b> больше не участвует в френдзоне с <b>{partner_name}</b>.\n"
                f"Хватит это терпеть!",
                parse_mode="HTML",
            )
        return

    # 3. ПРЕДЛОЖЕНИЕ
    if "предложение" in text:
        if not message.reply_to_message:
            await message.answer(
                "Чтобы сделать предложение, ответьте этой командой на сообщение человека!"
            )
            return

        user_from = message.from_user
        user_to = message.reply_to_message.from_user

        if user_from.id == user_to.id:
            await message.answer(
                "Самовлюбленность — это хорошо, но брак с самим собой мы не регистрируем."
            )
            return

        if user_to.is_bot:
            await message.answer("Роботы не умеют любить... 🤖💔")
            return

        # Проверка на наличие брака
        db = await get_db()
        for rec in db:
            ids = {rec["id1"], rec["id2"]}
            # Проверяем инициатора
            if user_from.id in ids:
                await message.answer(
                    f"Вы уже состоите в отношениях! Сначала разведитесь."
                )
                return
            # Проверяем того, кому предлагают
            if user_to.id in ids:
                await message.answer(f"Пользователь {user_to.full_name} уже занят(а)!")
                return

        builder = InlineKeyboardBuilder()
        builder.button(
            text="🥰 Да", callback_data=f"mry:yes:{user_from.id}:{user_to.id}"
        )
        builder.button(
            text="😐 Нет", callback_data=f"mry:no:{user_from.id}:{user_to.id}"
        )
        builder.button(
            text="🤡 Френдзона", callback_data=f"mry:fz:{user_from.id}:{user_to.id}"
        )
        builder.adjust(2, 1)

        await message.answer(
            f"💍 <b>{user_to.full_name}</b>, пользователь <b>{user_from.full_name}</b> делает вам предложение!\n"
            "Вы согласны заключить брак?",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


# --- ОБРАБОТЧИК КНОПОК (CALLBACK) ---


async def handle_callback(callback: CallbackQuery, bot):
    # data: mry:yes:12345:67890
    data_parts = callback.data.split(":")
    action = data_parts[1]
    from_id = int(data_parts[2])
    to_id = int(data_parts[3])

    if callback.from_user.id != to_id:
        await callback.answer(
            "Руки прочь! 😡 Это предложение не для вас!", show_alert=True
        )
        return

    name_to = callback.from_user.full_name
    try:
        chat = callback.message.chat
        member = await bot.get_chat_member(chat.id, from_id)
        name_from = member.user.full_name
    except:
        name_from = "Инициатор"

    if action == "no":
        await callback.message.edit_text(
            f"💔 <b>{name_to}</b> отклонил(а) предложение <b>{name_from}</b>.\nСердце разбито...",
            parse_mode="HTML",
        )

    elif action == "yes":
        new_record = {
            "type": "marriage",
            "date": int(time.time()),
            "id1": from_id,
            "name1": name_from,
            "id2": to_id,
            "name2": name_to,
        }
        await add_record(new_record)
        await callback.message.edit_text(
            f"🎉 <b>Горько!</b>\n\n<b>{name_from}</b> и <b>{name_to}</b> теперь официально в браке! 💍❤️",
            parse_mode="HTML",
        )

    elif action == "fz":
        new_record = {
            "type": "friendzone",
            "date": int(time.time()),
            "id1": from_id,
            "name1": name_from,
            "id2": to_id,
            "name2": name_to,
        }
        await add_record(new_record)
        await callback.message.edit_text(
            f"🚧 <b>{name_to}</b> решил(а) зафрендзонить <b>{name_from}</b>.\nТеперь вы лучшие друзья... навсегда. 🤡",
            parse_mode="HTML",
        )
