# tasks.py
import asyncio
from services import get_json, api_add_tg_list
from config import CHAT_ID


async def check_leavers_loop(bot):
    """Бесконечный цикл проверки участников"""
    print("👀 Запущен мониторинг участников (интервал 60 мин)")

    while True:
        try:
            await process_leavers(bot)
        except Exception as e:
            print(f"❌ Ошибка в цикле проверки: {e}")

        # Ждем 60 минут (3600 секунд)
        await asyncio.sleep(3600)


async def process_leavers(bot):
    # 1. Получаем "Старый список" (тех, кто был в базе)
    # Предполагаем, что api_get_tg_list.php возвращает список юзеров из таблицы tg_list
    old_data = await get_json("services/api_get_tg_list.php")

    # Собираем множество старых юзернеймов для быстрого поиска
    # (Учитываем структуру JSON, который возвращает ваш скрипт.
    # Если там roles -> users, то парсим так же, как в statuses.py)
    old_usernames = set()
    if old_data:
        # Если api_get_tg_list возвращает ту же структуру, что и api_users_json:
        for role in old_data:
            for user in role.get("users", []):
                uname = user.get("user_name", "")
                if uname:
                    old_usernames.add(uname.lower())  # храним в нижнем регистре

    # 2. Получаем "Всех зарегистрированных" (чтобы знать ID для проверки)
    all_users_data = await get_json("services/api_users_json.php")
    if not all_users_data:
        print("⚠️ Не удалось получить список пользователей для проверки.")
        return

    current_present_users = []  # Те, кто сейчас в чате

    # 3. Проверяем каждого через Telegram API
    for role in all_users_data:
        for user in role.get("users", []):
            user_id = user.get("user_id")
            username = user.get("user_name", "")
            full_name = user.get("name", "Неизвестный")

            if not user_id:
                continue

            try:
                # Спрашиваем у Телеграма: "Этот юзер еще в чате?"
                member = await bot.get_chat_member(CHAT_ID, user_id)

                # Статусы: member, administrator, creator, restricted (если просто мут)
                if member.status in [
                    "member",
                    "administrator",
                    "creator",
                    "restricted",
                ]:
                    current_present_users.append(username)

                # Статусы выхода: left, kicked (выгнан)
                elif member.status in ["left", "kicked"]:
                    # Проверяем: Был ли он раньше?
                    if username.lower() in old_usernames:
                        # ОН ВЫШЕЛ!
                        await bot.send_message(
                            CHAT_ID,
                            f"⚠️ <b>{full_name}</b> ({username}) покинул беседу :((",
                            parse_mode="HTML",
                        )
                        # Убираем из множества, чтобы не сработать дважды, если логика сложнее
                        old_usernames.discard(username.lower())

            except Exception as e:
                # Например, бот не админ или чат не найден
                # print(f"Не удалось проверить {user_id}: {e}")
                pass

    # 4. Обновляем базу (записываем текущих)
    # ВАЖНО: Ваш скрипт api_add_tg_list делает INSERT.
    # Если таблицу не очищать, она переполнится дублями.
    # В идеале нужно сделать api_clear_tg_list.php.
    # Но пока просто добавляем тех, кто есть.

    if current_present_users:
        # Тут можно вызвать скрипт очистки, если он будет
        await get_text("services/api_clear_tg_list.php")

        for uname in current_present_users:
            if uname:
                await api_add_tg_list(uname)

    print(f"✅ Проверка завершена. Активных участников: {len(current_present_users)}")
