import os
import re
import json
import importlib
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from config import GROUP_ID, PREFIXES
from services import vk_session, vk
from services import vk_session, vk, check_mute
from services import (
    vk_session,
    vk,
    check_mute,
    check_is_banned,
)  # <-- Добавили check_is_banned


# Для обработки кнопок импортируем логику напрямую (так надежнее)
from commands import maps, weapons

longpoll = VkBotLongPoll(vk_session, GROUP_ID)
commands_registry = {}


def load_commands():
    """Загружает файлы из папки commands"""
    if not os.path.exists("commands"):
        return

    for filename in os.listdir("commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"commands.{module_name}")
                if hasattr(module, "keys") and hasattr(module, "run"):
                    for key in module.keys:
                        commands_registry[key.lower()] = module.run
                    print(f"✅ Загружен: {filename}")
            except Exception as e:
                print(f"❌ Ошибка {filename}: {e}")


def parse_message(text):
    """Парсер команд"""
    if not text:
        return None
    sorted_cmds = sorted(commands_registry.keys(), key=len, reverse=True)

    esc_pref = [re.escape(p) for p in PREFIXES]
    esc_cmd = [re.escape(cmd) for cmd in sorted_cmds]

    pattern = re.compile(
        r"^(" + "|".join(esc_pref) + r")\s+(" + "|".join(esc_cmd) + r")(?:\s+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    match = pattern.match(text.strip())
    if match:
        _, cmd, args = match.groups()
        return {"command": cmd.lower(), "args": args.strip() if args else None}
    return None


if __name__ == "__main__":
    print("--- Запуск бота ---")
    load_commands()
    print("Бот слушает...")

    for event in longpoll.listen():
        # 1. ТЕКСТОВЫЕ СООБЩЕНИЯ И СОБЫТИЯ БЕСЕДЫ
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            peer_id = msg["peer_id"]
            user_id = msg["from_id"]

            # --- [1] ЗАЩИТА ОТ ВОЗВРАЩЕНИЯ ЗАБАНЕННЫХ (AUTO-KICK) ---
            # Проверяем "action" - это системное событие (кто-то вошел)
            if "action" in msg:
                action_type = msg["action"]["type"]

                if action_type in ["chat_invite_user", "chat_invite_user_by_link"]:
                    # Кто вошел (или кого пригласили)?
                    joined_id = msg["action"].get("member_id", user_id)

                    # Если этот человек в бане
                    if check_is_banned(peer_id, joined_id):
                        try:
                            # Кикаем мгновенно
                            chat_id = peer_id - 2000000000
                            vk.messages.removeChatUser(
                                chat_id=chat_id, user_id=joined_id
                            )
                            vk.messages.send(
                                peer_id=peer_id,
                                message=f"⛔ @id{joined_id} в бане. Вход воспрещен!",
                                random_id=0,
                            )
                        except Exception as e:
                            print(f"Ошибка авто-кика: {e}")
            # --------------------------------------------------------

            # --- [2] ПРОВЕРКА НА МУТ (Удаление сообщений) ---
            if check_mute(peer_id, user_id):
                try:
                    vk.messages.delete(
                        peer_id=peer_id,
                        conversation_message_ids=[msg["conversation_message_id"]],
                        delete_for_all=1,
                    )
                except:
                    pass
                continue
            # ------------------------------------------------

            # Далее идет обычная обработка команд...
            data = parse_message(msg["text"])
            if data:
                # ... твой код запуска команд ...
                cmd_func = commands_registry[data["command"]]
                try:
                    cmd_func(event, data["args"])
                except Exception as e:
                    print(f"Ошибка: {e}")

        # 2. НАЖАТИЯ КНОПОК
        elif event.type == VkBotEventType.MESSAGE_EVENT:
            payload = event.object.payload
            try:
                if payload.get("type") == "refresh_maps":
                    maps.handle_callback(event)
                elif payload.get("type") == "select_weapon":
                    weapons.handle_callback(event)
            except Exception as e:
                print(f"Ошибка callback: {e}")
