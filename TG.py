import asyncio
import logging
import os
import importlib

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from config import BOT_TOKEN, PREFIXES
from services import check_mute, check_is_banned, check_permissions, update_local_user
from aiogram.types import ContentType  # Не забудьте добавить в импорты вверху!

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Реестр команд
commands_registry = {}


def load_commands():
    """Динамически загружает модули из папки commands"""
    if not os.path.exists("commands"):
        print("Папка commands не найдена!")
        return

    commands_registry.clear()

    for filename in os.listdir("commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"commands.{module_name}")
                importlib.reload(module)

                if hasattr(module, "run"):
                    # Получаем права (из словаря PERMISSIONS или общей переменной)
                    module_perms_dict = getattr(module, "PERMISSIONS", {})
                    module_common_perm = getattr(module, "permissions", None)

                    if hasattr(module, "keys"):
                        for key in module.keys:
                            lower_key = key.lower()
                            req_perm = module_perms_dict.get(
                                lower_key, module_common_perm
                            )

                            commands_registry[lower_key] = {
                                "run": module.run,
                                "perm": req_perm,
                            }
                    print(f"✅ Загружен: {filename}")
            except Exception as e:
                print(f"❌ Ошибка загрузки {filename}: {e}")


# --- ОБРАБОТЧИК КНОПОК (CALLBACK) ---
from aiogram.types import CallbackQuery


@dp.callback_query()
async def handle_callbacks(callback: CallbackQuery):
    data = callback.data

    # Карты
    if data == "refresh_maps":
        from commands import maps

        await maps.handle_callback(callback, bot)

    # Оружие
    elif data.startswith("wp:") or data.startswith("wp_sel:"):
        from commands import weapons

        await weapons.handle_callback(callback, bot)

    # Браки
    elif data.startswith("mry:"):
        from commands import marriages

        await marriages.handle_callback(callback, bot)
    # Розыгрыши
    elif data.startswith("gw:"):
        from commands import giveaway

        await giveaway.handle_callback(callback, bot)
    try:
        await callback.answer()
    except:
        pass


# --- ОБРАБОТЧИК ВХОДА НОВЫХ УЧАСТНИКОВ ---
@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    # ЛОГ: Видим ли мы вход?
    print(f"DEBUG: Вход в чат! ({len(message.new_chat_members)} чел.)")

    for user in message.new_chat_members:
        # 1. Сохраняем в локальную базу (Обязательно проверьте импорт update_local_user!)
        try:
            await update_local_user(user.id, user.username, user.full_name)
        except Exception as e:
            print(f"❌ Ошибка сохранения юзера: {e}")

        # 2. Проверка бана
        if check_is_banned(message.chat.id, user.id):
            try:
                await bot.ban_chat_member(message.chat.id, user.id)
                await message.answer(
                    f"⛔ Пользователь {user.full_name} в черном списке. Изгнан."
                )
                await bot.unban_chat_member(message.chat.id, user.id)
            except Exception as e:
                print(f"Ошибка кика: {e}")
            continue

        # 3. ПРИВЕТСТВИЕ
        if not user.is_bot:
            rules_link = "https://sites.google.com/view/surpassrules/главная-страница"

            # Текст (HTML разметка)
            welcome_text = (
                f"🦅 <b>Welcome to SURPASS Clan, {user.mention_html()}!</b>\n\n"
                f"Рады видеть тебя в наших рядах. Вся важная информация уже ждет тебя в 📌 <b>закрепе</b>, но вот краткий курс молодого бойца:\n\n"
                f"⚔️ <b>Система поощрений:</b>\n"
                f"Мы ценим активность! Принеси клану <b>3000 опыта</b> и получи награду на выбор:\n"
                f"• Любое оружие из альтернативного магазина\n"
                f"• Монеты\n"
                f"• Реальные деньги\n\n"
                f"👑 <b>Управление кланом:</b>\n"
                f"👤 Глава: @forzejager (Степан)\n"
                f"✨ Душа клана и Маскот: @bemysur (Елена)\n"
                f"😈 Заместитель: @slavyanskoeghetto (Крестик)\n\n"
                f"📜 <b>Важно:</b>\n"
                f"Обязательно ознакомься с <a href='{rules_link}'>Правилами клана</a>!\n\n"
                f"🤖 <b>О себе:</b>\n"
                f"Я — бот этого клана. Помогаю с инфой, статистикой и развлечениями.\n"
                f"👉 Уточнить мои возможности можно у ребят в чате.\n\n"
                f"<i>Удачи в боях и добро пожаловать в семью!</i>"
            )

            print(f"DEBUG: Отправляю приветствие для {user.full_name}")

            try:
                # Пробуем ответить на сообщение о входе
                await message.reply(
                    welcome_text, parse_mode="HTML", disable_web_page_preview=True
                )
            except Exception as e:
                print(f"❌ Не удалось ответить реплаем: {e}")
                # Если не вышло (например, сообщение о входе удалено), пишем просто в чат
                try:
                    await message.answer(
                        welcome_text, parse_mode="HTML", disable_web_page_preview=True
                    )
                except Exception as e2:
                    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ОТПРАВКИ: {e2}")


# --- ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip()

    mute_type = check_mute(chat_id, user_id)

    if mute_type:
        should_delete = False
        msg_type = message.content_type  # photo, video, text, sticker...

        # Логика проверки типов
        if mute_type == "all":
            should_delete = True

        elif mute_type == "media":
            # Медиа мут: фото, видео, кружочки, гифки, стикеры, документы, аудио
            if msg_type in [
                ContentType.PHOTO,
                ContentType.VIDEO,
                ContentType.VIDEO_NOTE,
                ContentType.ANIMATION,
                ContentType.STICKER,
                ContentType.AUDIO,
                ContentType.VOICE,
                ContentType.DOCUMENT,
            ]:
                should_delete = True

        elif mute_type == "photo" and msg_type == ContentType.PHOTO:
            should_delete = True

        elif mute_type == "video" and msg_type in [
            ContentType.VIDEO,
            ContentType.VIDEO_NOTE,
        ]:
            should_delete = True

        elif mute_type == "animation" and msg_type == ContentType.ANIMATION:
            should_delete = True

        elif mute_type == "sticker" and msg_type == ContentType.STICKER:
            should_delete = True

        if should_delete:
            try:
                await message.delete()
            except:
                pass
            return  # Прерываем обработку, команды тоже не сработают

    # 2. ПОИСК ПРЕФИКСА (СТРОГАЯ ПРОВЕРКА)
    text_lower = text.lower()
    used_prefix = None

    # Сортируем префиксы по длине, чтобы "лилит" сработало раньше "л"
    sorted_prefixes = sorted(PREFIXES, key=len, reverse=True)

    for p in sorted_prefixes:
        if text_lower.startswith(p):
            used_prefix = p
            break

    # ЕСЛИ ПРЕФИКС НЕ НАЙДЕН — ИГНОРИРУЕМ СООБЩЕНИЕ
    if not used_prefix:
        return

    # 3. ПАРСИНГ КОМАНДЫ
    # Убираем префикс из текста
    search_text = text_lower[len(used_prefix) :].strip()

    command_found = None
    args = None

    # Сортируем команды, чтобы длинные искались первыми ("клан вк" раньше "клан")
    sorted_keys = sorted(commands_registry.keys(), key=len, reverse=True)

    for key in sorted_keys:
        if search_text.startswith(key):
            # Проверяем, что это целое слово (или конец строки)
            # Чтобы команда "бан" не срабатывала на "банан"
            rest = search_text[len(key) :]
            if not rest or rest.startswith(" "):
                command_found = key
                # Аргументы берем из ОРИГИНАЛЬНОГО текста (чтобы сохранить регистр)
                # Вычисляем смещение: длина префикса + длина ключа
                # Но проще так: берем исходный текст, убираем префикс, стрипаем, убираем ключ

                raw_no_prefix = text[len(used_prefix) :].strip()
                args = raw_no_prefix[len(key) :].strip()
                break

    # 4. ЗАПУСК
    if command_found:
        cmd_data = commands_registry[command_found]
        handler = cmd_data["run"]
        required_perm = cmd_data["perm"]

        # Проверка прав
        if not await check_permissions(message, required_perm, bot):
            # Можно включить ответ, если хотите уведомлять о нехватке прав
            # await message.reply("⛔ Нет прав.")
            return

        try:
            await handler(message, args, bot)
        except Exception as e:
            print(f"Ошибка при выполнении '{command_found}': {e}")
            await message.answer("⚠️ Произошла ошибка при выполнении команды.")


# --- ЗАПУСК ---
from tasks import check_leavers_loop


async def main():
    print("--- Запуск Telegram бота ---")
    load_commands()
    print("Бот слушает...")

    # Фоновые задачи
    asyncio.create_task(check_leavers_loop(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
