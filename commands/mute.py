# commands/mute.py
import re
import time
from services import vk, extract_mention, add_mute, remove_mute

keys = ["мут", "mute", "размут", "unmute"]


def parse_time(args):
    """Превращает '5м', '1ч' в секунды"""
    if not args:
        return 30 * 24 * 60 * 60  # По умолчанию 30 дней

    # Ищем числа и буквы (например: 10м)
    match = re.search(r"(\d+)\s*(с|м|ч|д|s|m|h|d)?", args.lower())
    if not match:
        return 30 * 24 * 60 * 60

    val = int(match.group(1))
    unit = match.group(2)

    if unit in ["с", "s"]:
        return val
    if unit in ["м", "m"]:
        return val * 60
    if unit in ["ч", "h"]:
        return val * 3600
    if unit in ["д", "d"]:
        return val * 86400

    return val * 60  # Если не указано, считаем минуты


def run(event, args):
    peer_id = event.obj.message["peer_id"]
    text = event.obj.message["text"].lower()

    # 1. Логика РАЗМУТА
    if "размут" in text or "unmute" in text:
        if not args:
            vk.messages.send(
                peer_id=peer_id, message="Кого размутить? Укажи @ссылку", random_id=0
            )
            return

        target_id = extract_mention(args)
        if target_id:
            if remove_mute(peer_id, target_id):
                vk.messages.send(
                    peer_id=peer_id,
                    message=f"✅ @id{target_id} снова может говорить.",
                    random_id=0,
                )
            else:
                vk.messages.send(
                    peer_id=peer_id,
                    message="Этот пользователь не был в муте.",
                    random_id=0,
                )
        return

    # 2. Логика МУТА
    if not args:
        vk.messages.send(
            peer_id=peer_id,
            message="Укажи кого замутить. Пример: мут @user 1ч",
            random_id=0,
        )
        return

    target_id = extract_mention(args)
    if not target_id:
        vk.messages.send(
            peer_id=peer_id, message="Не удалось найти пользователя.", random_id=0
        )
        return

    # Вычисляем время (убираем меншн из аргументов, чтобы найти время)
    # args сейчас выглядит как "[id1|Vasya] 10м"
    clean_args = re.sub(r"\[.*?\]|@\w+", "", args).strip()
    seconds = parse_time(clean_args)

    # Добавляем в базу
    add_mute(peer_id, target_id, seconds)

    # Формируем красивый ответ
    readable_time = ""
    if seconds >= 86400:
        readable_time = f"{round(seconds/86400, 1)} дн."
    elif seconds >= 3600:
        readable_time = f"{round(seconds/3600, 1)} ч."
    elif seconds >= 60:
        readable_time = f"{round(seconds/60, 1)} мин."
    else:
        readable_time = f"{seconds} сек."

    vk.messages.send(
        peer_id=peer_id,
        message=f"🤫 @id{target_id} получил мут на {readable_time}\nЕго сообщения будут удаляться.",
        random_id=0,
    )
