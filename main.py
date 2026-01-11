# main.py
import asyncio
import logging
import os
import importlib
import re

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import CommandStart

from config import BOT_TOKEN, PREFIXES
from services import check_mute, check_is_banned
from services import check_permissions

from tasks import check_leavers_loop  # <--- Импортируем

from aiogram.types import CallbackQuery

# Настройка логирования (чтобы видеть ошибки в консоли)
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Реестр команд: {"ключ": функция_run}
commands_registry = {}


def load_commands():
    if not os.path.exists("commands"):
        return

    commands_registry.clear()

    for filename in os.listdir("commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"commands.{module_name}")
                importlib.reload(module)

                if hasattr(module, "run"):
                    # 1. Ищем словарь PERMISSIONS в модуле (НОВАЯ ФИШКА)
                    # Пример в файле:
                    # PERMISSIONS = {
                    #    "мой айди": "edit_me",
                    #    "дай айди": "edit_other"
                    # }
                    #
                    # 2. Или ищем общую переменную permissions (как раньше)
                    # permissions = "ban"

                    module_perms_dict = getattr(module, "PERMISSIONS", {})
                    module_common_perm = getattr(module, "permissions", None)

                    # Если keys определен
                    if hasattr(module, "keys"):
                        for key in module.keys:
                            lower_key = key.lower()

                            # Определяем право для КОНКРЕТНОЙ команды
                            # Приоритет: Словарь -> Общая переменная -> None
                            req_perm = module_perms_dict.get(
                                lower_key, module_common_perm
                            )

                            commands_registry[lower_key] = {
                                "run": module.run,
                                "perm": req_perm,
                            }
                    print(f"✅ Загружен: {filename}")
            except Exception as e:
                print(f"❌ Ошибка {filename}: {e}")


# --- ОБРАБОТКА ВХОДА ПОЛЬЗОВАТЕЛЕЙ (Auto-Kick) ---
@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    """Если заходит забаненный пользователь — кикаем"""
    for user in message.new_chat_members:
        if check_is_banned(message.chat.id, user.id):
            try:
                await bot.ban_chat_member(message.chat.id, user.id)
                await message.answer(
                    f"⛔ Пользователь {user.full_name} в черном списке. Изгнан."
                )
                # Сразу разбаниваем (unban), чтобы он мог войти, если его уберут из БД,
                # но технически kick в ТГ = ban.
                await bot.unban_chat_member(message.chat.id, user.id)
            except Exception as e:
                print(f"Не удалось кикнуть: {e}")


# --- ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message()
async def handle_message(message: Message):
    # Игнорируем сообщения без текста (стикеры и т.д., если это не вход юзера)
    if not message.text:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip()

    # 1. ПРОВЕРКА НА МУТ
    # Если юзер в муте — удаляем сообщение и выходим
    if check_mute(chat_id, user_id):
        try:
            await message.delete()
        except:
            pass  # Бот не админ или нельзя удалить
        return

    # 2. ПАРСИНГ КОМАНДЫ
    text_lower = text.lower()
    command_found = None
    args = None

    # Сортируем ключи по длине (чтобы "клан вк" сработал раньше "клан")
    sorted_keys = sorted(commands_registry.keys(), key=len, reverse=True)

    # Логика поиска:
    # 1. Проверяем точное совпадение ключа в начале (без префикса) -> на случай если кто-то пишет просто "бан"
    # 2. Проверяем префикс + ключ -> "л бан"

    # Попытка найти префикс
    used_prefix = None
    for p in PREFIXES:
        if text_lower.startswith(p):
            used_prefix = p
            break

    # Текст для анализа (либо всё сообщение, либо без префикса)
    search_text = text_lower
    if used_prefix:
        search_text = text_lower[len(used_prefix) :].strip()

    # Ищем команду в начале search_text
    for key in sorted_keys:
        if search_text.startswith(key):
            # Проверяем, что это слово целиком (чтобы "бан" не сработал на "банан")
            rest = search_text[len(key) :]
            if not rest or rest.startswith(" "):
                command_found = key
                # Аргументы — это всё, что после команды (из оригинального текста, чтобы сохранить регистр аргументов)
                # Вычисляем смещение: длина префикса (если был) + длина ключа
                offset = (len(used_prefix) if used_prefix else 0) + len(key)
                # Если были пробелы между префиксом и командой или командой и аргументами, strip() их съел,
                # поэтому надежнее брать args из search_text

                # Проще: берем исходный текст, убираем префикс (если был), убираем ключ, стрипаем
                raw_text_no_prefix = text[len(used_prefix) :] if used_prefix else text
                # Находим начало команды (оно должно быть в начале strip-нутой строки)
                # Но для простоты args возьмем как остаток:
                args = raw_text_no_prefix.strip()[len(key) :].strip()
                break

    # 3. ЗАПУСК КОМАНДЫ
    if command_found:
        cmd_data = commands_registry[command_found]
        handler = cmd_data["run"]
        required_perm = cmd_data["perm"] # Строка, например "ban" или "edit_other"

        # === ПРОВЕРКА ПРАВ ===
        # Передаем требуемое право в сервис
        if not await check_permissions(message, required_perm, bot):
            # Можно сделать красивее: если прав нет, бот молчит или пишет ошибку
            await message.reply(f"⛔ У вас нет прав ({required_perm}) для этой команды.")
            return
        # =====================

        try:
            await handler(message, args, bot)
        except Exception as e:
            print(f"Ошибка при выполнении команды '{command_found}': {e}")
            await message.reply(f"❌ Ошибка при выполнении команды.")


# --- ОБРАБОТЧИК КНОПОК (CALLBACK) ---
@dp.callback_query()
async def handle_callbacks(callback: CallbackQuery):
    data = callback.data

    # Обработка карт
    if data == "refresh_maps":
        # Импортируем функцию из модуля maps
        # (Так как commands_registry хранит только run, импортируем тут)
        from commands import maps

        await maps.handle_callback(callback, bot)

    # Обработка оружия
    elif data.startswith("wp:"):
        from commands import weapons

        await weapons.handle_callback(callback, bot)

    # Не забываем отвечать на колбэк, чтобы убрались "часики"
    # (Функции выше сами отвечают, но если нет — safety net)
    try:
        await callback.answer()
    except:
        pass


# --- ТОЧКА ВХОДА ---
async def main():
    print("--- Запуск Telegram бота ---")
    load_commands()
    print("Бот слушает...")

    # Запускаем фоновую задачу
    asyncio.create_task(check_leavers_loop(bot))  # <--- ВОТ ТУТ
    
    # Удаляем вебхуки (если были) и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
