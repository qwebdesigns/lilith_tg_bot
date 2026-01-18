# commands/mute.py
import re
import time
from services import add_mute, remove_mute

keys = ["мут", "mute", "размут", "unmute"]

PERMISSIONS = {"мут": "mute_users", "размут": "mute_users"}


def parse_time(args):
    if not args:
        return 30 * 60
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
    text = message.text.lower()  # Весь текст: "л мут фото 1ч"

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
            "🤫 Ответьте на сообщение. Пример: <code>мут фото 1ч</code>",
            parse_mode="HTML",
        )
        return

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.full_name

    # 1. ОПРЕДЕЛЯЕМ ТИП МУТА
    mute_type = "all"
    type_text = "полный мут"

    # Убираем ключевые слова из аргументов, чтобы не сломать парсинг времени
    clean_args = args

    if "фото" in text:
        mute_type = "photo"
        type_text = "мут картинок"
        clean_args = clean_args.replace("фото", "")
    elif "видео" in text:
        mute_type = "video"
        type_text = "мут видео"
        clean_args = clean_args.replace("видео", "")
    elif "гиф" in text:
        mute_type = "animation"
        type_text = "мут GIF"
        clean_args = clean_args.replace("гиф", "")
    elif "стикер" in text:  # стикеры, стикер
        mute_type = "sticker"
        type_text = "мут стикеров"
        clean_args = re.sub(r"стикер[а-я]*", "", clean_args)
    elif "медиа" in text:
        mute_type = "media"
        type_text = "мут медиа (фото/видео/гиф/стикеры)"
        clean_args = clean_args.replace("медиа", "")

    # 2. Парсим время
    seconds = parse_time(clean_args)

    # 3. Сохраняем
    add_mute(chat_id, target_id, seconds, mute_type)

    readable = f"{seconds} сек."
    if seconds >= 3600:
        readable = f"{round(seconds/3600, 1)} ч."
    elif seconds >= 60:
        readable = f"{round(seconds/60, 1)} мин."

    await message.answer(
        f"🤫 {target_name} получил <b>{type_text}</b> на {readable}.", parse_mode="HTML"
    )
