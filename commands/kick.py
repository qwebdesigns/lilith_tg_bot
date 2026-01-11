from services import vk, extract_mention

keys = ["кик", "kick", "выгнать"]


def run(event, args):
    peer_id = event.obj.message["peer_id"]

    # Получаем ID беседы (chat_id = peer_id - 2000000000)
    if peer_id < 2000000000:
        vk.messages.send(
            peer_id=peer_id, message="Команда работает только в беседах.", random_id=0
        )
        return

    chat_id = peer_id - 2000000000

    # Проверяем аргументы
    target_id = extract_mention(args)

    # Если аргумента нет, и это ответ на сообщение (reply)
    if not target_id and "reply_message" in event.obj.message:
        target_id = event.obj.message["reply_message"]["from_id"]

    if not target_id:
        vk.messages.send(
            peer_id=peer_id,
            message="Кого кикнуть? Укажи @user или ответь на сообщение.",
            random_id=0,
        )
        return

    # Пытаемся выгнать
    try:
        vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id)
        vk.messages.send(
            peer_id=peer_id,
            message=f"👋 Пользователь @id{target_id} исключен.",
            random_id=0,
        )
    except Exception as e:
        vk.messages.send(
            peer_id=peer_id,
            message=f"Не удалось кикнуть (нет прав админа или это админ).\nОшибка: {e}",
            random_id=0,
        )
