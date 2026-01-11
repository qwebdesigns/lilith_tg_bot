import re
import time
from services import add_mute, remove_mute

keys = ["мут", "mute", "размут", "unmute"]

PERMISSIONS = {
    "мут": 'mute_users',
    "размут": 'mute_users'
    }

def parse_time(args):
    """Превращает '5м', '1ч' в секунды"""
    if not args:
        return 30 * 60  # По умолчанию 30 мин

    # Ищем число + букву
    match = re.search(r"(\d+)\s*(с|м|ч|д|s|m|h|d)?", args.lower())
    if not match:
        return 30 * 60

    val = int(match.group(1))
    unit = match.group(2)

    if unit in ["с", "s"]:
        return val
    if unit in ["м", "m", None]:
        return val * 60
    if unit in ["ч", "h"]:
        return val * 3600
    if unit in ["д", "d"]:
        return val * 86400
    return val * 60


async def run(message, args, bot):
    chat_id = message.chat.id
    text = message.text.lower()

    # --- РАЗМУТ ---
    if "размут" in text or "unmute" in text:
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id

        if target_id and remove_mute(chat_id, target_id):
            await message.answer(
                f"✅ {message.reply_to_message.from_user.full_name} снова может говорить."
            )
        else:
            await message.answer(
                "Пользователь не был в муте или вы не ответили на сообщение."
            )
        return

    # --- МУТ ---
    if not message.reply_to_message:
        await message.answer(
            "🤫 Ответьте на сообщение, чтобы замутить. Пример: <code>мут 1ч</code>",
            parse_mode="HTML",
        )
        return

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.full_name

    # Парсим время из аргументов (args = текст после команды "мут")
    seconds = parse_time(args)

    # Добавляем в базу (чтобы бот удалял сообщения)
    add_mute(chat_id, target_id, seconds)

    # Форматируем вывод времени
    readable = f"{seconds} сек."
    if seconds >= 3600:
        readable = f"{round(seconds/3600, 1)} ч."
    elif seconds >= 60:
        readable = f"{round(seconds/60, 1)} мин."

    await message.answer(
        f"🤫 {target_name} получил мут на {readable}.\nЕго сообщения будут удаляться."
    )
