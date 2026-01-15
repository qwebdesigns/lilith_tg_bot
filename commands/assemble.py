import html
from services import get_json

keys = ["общий сбор"]

PERMISSIONS = {
    "общий сбор": "assemble"
}

# Лимит Телеграма (оставляем запас под HTML теги)
MAX_MESSAGE_LENGTH = 4000 
# Невидимый пробел (Zero Width Space)
ZWS = "\u200b"

async def run(message, args, bot):
    await message.answer("📣 <b>Приняла! Собираю всех!...</b>", parse_mode="HTML")
    
    data = await get_json("services/api_users_json.php")
    
    if not data:
        await message.answer("❌ Ошибка: Не удалось получить список участников.")
        return

    for group in data:
        role_name = group.get("name_role", "Без названия")
        role_id = group.get("role_id", "?")
        users = group.get("users", [])

        if not users:
            continue

        # Видимый заголовок
        header = f"🛡 <b>{html.escape(role_name)} ({role_id})</b> - Общий сбор! 📢"
        
        # Собираем НЕВИДИМЫЕ меншоны
        invisible_mentions = []
        for user in users:
            user_id = user.get("user_id")
            
            # Пинг работает только по ID через tg://user
            if user_id:
                # Создаем ссылку, внутри которой пустота (невидимый пробел)
                # Телеграм увидит ссылку на юзера и отправит ему уведомление,
                # но визуально в сообщении ничего не добавится.
                mention = f'<a href="tg://user?id={user_id}">{ZWS}</a>'
                invisible_mentions.append(mention)
            
            # Если есть только username без ID, скрыто пингануть нельзя. 
            # (Можно добавить @username, но тогда он будет виден).
            # Поэтому пингуем только тех, у кого есть ID.

        if not invisible_mentions:
            continue

        # Разбивка на сообщения (так как HTML-код невидимых ссылок всё равно занимает место)
        current_text = header
        
        for mention in invisible_mentions:
            # Проверяем длину HTML кода
            if len(current_text) + len(mention) > MAX_MESSAGE_LENGTH:
                # Отправляем текущую пачку
                await message.answer(current_text, parse_mode="HTML")
                # Начинаем новую пачку (опять с заголовком, чтобы было понятно, кто это)
                current_text = header + mention
            else:
                current_text += mention

        # Отправляем остаток
        if current_text:
            await message.answer(current_text, parse_mode="HTML")

    await message.answer("✅ <b>Сбор объявлен!</b>", parse_mode="HTML")