import html
from services import get_json

keys = ["статусы", "состав", "список"]

# Права: None = доступно всем.
# Если хотите ограничить, напишите: "статусы": "edit_other"
PERMISSIONS = {
    "статусы": 'statuses',
    "состав": 'sostav',
    "список": 'list'}


async def run(message, args, bot):
    # 1. Получаем данные
    data = await get_json("services/api_users_json.php")

    if not data:
        await message.answer("❌ Не удалось получить список (ошибка API).")
        return

    # 2. Формируем текст
    # Телеграм имеет лимит ~4096 символов на сообщение.
    # Будем собирать текст и если он длинный — отправлять частями.

    messages_to_send = []
    current_text = ""

    for group in data:
        role_name = group.get("name_role", "Без названия")
        role_id = group.get("role_id", "?")
        users = group.get("users", [])

        # Заголовок группы
        group_header = f"\n<b>{html.escape(role_name)} ({role_id})</b>\n"

        # Собираем список участников группы
        users_list_str = ""
        if not users:
            users_list_str = "<i>(Пусто)</i>\n"
        else:
            for idx, user in enumerate(users, 1):
                name = user.get("name", "Неизвестный")
                user_id = user.get("user_id", "")
                user_name = user.get("user_name", "")  # @username
                game_name = user.get("game_name", "")

                # Экранируем, чтобы спецсимволы в никах не ломали HTML
                safe_name = html.escape(name)
                safe_game = (
                    html.escape(game_name) if game_name else "<i>нет игрового ника</i>"
                )

                # ЛОГИКА ССЫЛКИ
                # Если есть юзернейм (@...), ссылаемся на него
                if user_name and user_name.startswith("@"):
                    # Убираем собаку для ссылки
                    clean_username = user_name[1:]
                    link = f"https://t.me/{clean_username}"
                else:
                    # Иначе используем ID (работает только в мобильных/десктоп клиентах)
                    link = f"tg://user?id={user_id}"

                # Формат строки: 1) Имя - Игровой ник
                users_list_str += (
                    f'{idx}) <a href="{link}">{safe_name}</a> — {safe_game}\n'
                )

        # Проверяем длину будущего сообщения
        # Если добавление этой группы превысит лимит (берем 4000 с запасом),
        # то сохраняем текущий текст и начинаем новый.
        if len(current_text) + len(group_header) + len(users_list_str) > 4000:
            messages_to_send.append(current_text)
            current_text = ""

        current_text += group_header + users_list_str

    # Добавляем остаток текста
    if current_text:
        messages_to_send.append(current_text)

    # 3. Отправляем всё
    if not messages_to_send:
        await message.answer("Список пуст.")
        return

    for chunk in messages_to_send:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)
