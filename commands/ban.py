from services import vk, extract_mention, add_ban, remove_ban

keys = ["бан", "ban", "разбан", "unban"]


def run(event, args):
    peer_id = event.obj.message["peer_id"]
    text = event.obj.message["text"].lower()

    # Вычисляем chat_id для кика
    chat_id = peer_id - 2000000000 if peer_id > 2000000000 else None

    # Поиск ID цели
    target_id = extract_mention(args)
    if not target_id and "reply_message" in event.obj.message:
        target_id = event.obj.message["reply_message"]["from_id"]

    if not target_id:
        vk.messages.send(
            peer_id=peer_id, message="Укажите пользователя (@user).", random_id=0
        )
        return

    # --- ЛОГИКА РАЗБАНА ---
    if "разбан" in text or "unban" in text:
        if remove_ban(peer_id, target_id):
            vk.messages.send(
                peer_id=peer_id,
                message=f"✅ @id{target_id} удален из черного списка.",
                random_id=0,
            )
        else:
            vk.messages.send(
                peer_id=peer_id, message="Пользователя нет в бане.", random_id=0
            )
        return

    # --- ЛОГИКА БАНА ---
    # 1. Заносим в базу
    add_ban(peer_id, target_id)

    # 2. Кикаем из беседы прямо сейчас
    kick_status = "и исключен"
    if chat_id:
        try:
            vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id)
        except:
            kick_status = "но я не смог его кикнуть (нет прав?)"

    vk.messages.send(
        peer_id=peer_id,
        message=f"⛔ Пользователь @id{target_id} забанен {kick_status}.\nЕсли он вернется — я кикну его снова.",
        random_id=0,
    )
