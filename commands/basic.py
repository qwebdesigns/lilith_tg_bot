from services import get_text, extract_mention

keys = ["айди", "участник"]

PERMISSIONS = {
    "айди": "my_id",
    "участник": "about_me"
}

async def run(message, args, bot):
    text = message.text.lower()

    # --- Команда АЙДИ ---
    if "айди" in text:
        target_id = message.from_user.id
        target_name = message.from_user.full_name

        # Если это ответ на сообщение
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.full_name

        await message.answer(
            f"👤 {target_name}\n🆔 ID: <code>{target_id}</code>", parse_mode="HTML"
        )

    # --- Команда УЧАСТНИК ---
    elif "участник" in text:
        # Пытаемся найти аргумент
        target = args
        if not target and message.reply_to_message:
            # Если ответили на сообщение, берем ID того человека
            target = message.reply_to_message.from_user.id

        if not target:
            # Если нет аргументов, берем себя
            target = message.from_user.id

        # Делаем запрос к PHP
        info = await get_text(f"player_get_bot.php?link={target}")
        await message.answer(info)
