from services import api_save_user

# Ключевые слова, на которые реагирует бот
# Порядок важен: более длинные фразы лучше ставить раньше,
# чтобы "мой айди" не сработал как просто "айди"
keys = ["мой айди", "дай айди", "мне ник", "ник", "платформа", "статус", "регистрация"]

PERMISSIONS = {
    "мой айди": "edit_me",  # Право редактировать себя
    "мне ник": "edit_me",
    "дай айди": "edit_other",  # Право редактировать других
    "ник": "edit_other",
    "платформа": "edit_other",
    "статус": "set_role",  # Отдельное право на смену ролей (если нужно)
    "регистрация": None,  # Разрешено всем (None или пустая строка)
}

async def run(message, args, bot):
    text = message.text.lower()
    clean_args = args.strip()

    # 1. ОПРЕДЕЛЯЕМ ТИП КОМАНДЫ И ПОЛЕ
    # db_field: поле в базе
    # force_reply: требует ли команда обязательного ответа на сообщение
    # is_self: принудительно ли это изменение для себя

    db_field = None
    force_reply = False
    is_self = False

    # --- ЛОГИКА АЙДИ ---
    if "мой айди" in text:
        db_field = "game_id"
        is_self = True
    elif "дай айди" in text:
        db_field = "game_id"
        # Тут можно и реплаем, и просто указать ID цифрами, оставим гибко

    # --- ЛОГИКА НИКА ---
    elif "мне ник" in text:
        db_field = "game_name"
        is_self = True
    elif "ник" in text:
        db_field = "game_name"

    # --- ЛОГИКА СТАТУСА (АДМИНКА) ---
    elif "статус" in text:
        db_field = "admin_id"
        force_reply = True  # По условию: "только другие могут (ответ на сообщение)"

    # --- ЛОГИКА ПЛАТФОРМЫ ---
    elif "платформа" in text:
        db_field = "game_platform"

    # --- ПРОСТО РЕГИСТРАЦИЯ ---
    elif "регистрация" in text:
        # Ничего не меняем, просто отправляем данные профиля
        pass

    else:
        # Если как-то попали сюда без команды
        return

    # 2. ОПРЕДЕЛЯЕМ ЦЕЛЬ (Target User)
    target_user = None
    value = clean_args

    # Если команда требует реплая ("статус"), но его нет
    if force_reply and not message.reply_to_message:
        await message.answer(
            "⚠️ Эту команду нужно писать в ответ на сообщение пользователя."
        )
        return

    # ВАРИАНТ А: Явный приказ "себе" (мой айди, мне ник)
    if is_self:
        target_user = message.from_user

    # ВАРИАНТ Б: Ответ на сообщение (Reply) -> Цель тот, кому ответили
    elif message.reply_to_message:
        target_user = message.reply_to_message.from_user

    # ВАРИАНТ В: Указан числовой ID в аргументах (например: л дай айди 12345678 555)
    # Пытаемся понять, первое слово это ID юзера или значение?
    else:
        parts = clean_args.split()
        if parts and parts[0].isdigit() and len(parts) > 1:
            # Если первое слово цифры и есть что-то еще (значение), считаем первое слово ID цели
            # НО: Если мы меняем 'game_id', то аргумент сам по себе цифра.
            # Если команда "л дай айди 555", то 555 это значение, а цель - я? Или цель должна быть указана?
            # Давайте сделаем безопасно: если нет реплая и не "мой...", цель = отправитель.
            target_user = message.from_user
        else:
            target_user = message.from_user

    # 3. ФОРМИРУЕМ ДАННЫЕ ДЛЯ ОТПРАВКИ
    # Эти поля берутся автоматически из Телеграма (для слежки/актуализации)
    post_data = {
        "user_id": target_user.id,
        "name": target_user.full_name,  # Автоматически ФИО
        "user_name": (
            f"@{target_user.username}" if target_user.username else ""
        ),  # Автоматически @username
        # admin_id в PHP скрипте используется как "какую роль поставить", а не "кто меняет".
        # Поэтому мы его отправляем только если меняем статус.
    }

    # Если мы меняем конкретное поле
    if db_field:
        if not value:
            await message.answer("⚠️ Вы не указали значение!")
            return

        # Записываем значение в нужное поле
        post_data[db_field] = value

    # 4. ОТПРАВЛЯЕМ В PHP
    await message.answer("⏳ Обновляю базу...")
    response = await api_save_user(post_data)

    # 5. ОТВЕТ
    if response.get("status") == "success":
        # Красивое уведомление
        field_names = {
            "game_id": "Game ID",
            "game_name": "Игровой ник",
            "game_platform": "Платформа",
            "admin_id": "Статус (Role ID)",
        }
        what_changed = field_names.get(db_field, "Профиль")

        await message.answer(
            f"✅ <b>{what_changed}</b> для пользователя <b>{target_user.full_name}</b> обновлен.\n"
            f"Теперь: <code>{value}</code>",
            parse_mode="HTML",
        )
    else:
        error = response.get("message", "Неизвестная ошибка")
        print(f"Ошибка при сохранении пользователя: {error}")
        await message.answer(f"❌ Ошибка БД: {error}")
