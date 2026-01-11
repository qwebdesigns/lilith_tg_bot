import json
import os
import time
from services import get_text

# На какие команды реагировать
keys = ["кто я"]

PERMISSIONS = {
    "кто я": 'whoami'
    }

# Время кулдауна в секундах (например, 4 часа = 14400 сек)
# Можешь поменять на свое значение
COOLDOWN_SECONDS = 14400

DATA_FILE = "whoami.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


async def run(message, args, bot):
    user_id = str(message.from_user.id)
    name = message.from_user.full_name  # Имя + Фамилия (если есть)

    # Загружаем базу
    data = load_data()
    now_ts = int(time.time())

    # --- ПРОВЕРКА КУЛДАУНА ---
    if user_id in data:
        last_time = data[user_id].get("time", 0)
        cached_response = data[user_id].get("response", "")

        # Сколько прошло времени
        time_passed = now_ts - last_time

        # Если прошло меньше чем надо
        if time_passed < COOLDOWN_SECONDS:
            time_remaining = COOLDOWN_SECONDS - time_passed

            # Красивый формат времени (чч. мм.)
            hours = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            time_str = f"{hours} ч. {minutes} мин."

            # Отправляем старый ответ + таймер
            await message.answer(
                f'{cached_response}\n\n⏳ До твоего нового "кто я" осталось: {time_str}'
            )
            return

    # --- ГЕНЕРАЦИЯ НОВОЙ ФРАЗЫ ---
    # Отправляем статус "печатает", пока ждем ответ от сайта
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Делаем запрос к твоему PHP скрипту
        random_phrase = await get_text("random_phrase.php")
        random_phrase = random_phrase.strip()

        # Если API вернуло ошибку или пустоту
        if not random_phrase or "Ошибка" in random_phrase:
            random_phrase = "загадка"

    except Exception:
        random_phrase = "загадка"

    # Формируем сообщение
    result_message = f"💬 {name}, вы - {random_phrase}."

    # --- СОХРАНЕНИЕ ---
    data[user_id] = {"time": now_ts, "response": result_message}
    save_data(data)

    await message.answer(result_message)
