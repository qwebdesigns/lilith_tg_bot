keys = ["кик","выгнать"]

PERMISSIONS = {
    "кик": "kick",
    'выгнать': 'kick_2'
}

async def run(message, args, bot):
    # Проверка на личку
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах.")
        return

    # Ищем цель (лучше всего через Reply)
    target_id = None
    target_name = "Пользователь"

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name

    if not target_id:
        await message.answer(
            "⚠️ Ответьте на сообщение пользователя, которого нужно кикнуть."
        )
        return

    try:
        # В Telegram кик = бан + разбан
        await bot.ban_chat_member(message.chat.id, target_id)
        await bot.unban_chat_member(message.chat.id, target_id)

        await message.answer(f"👋 {target_name} был исключен.")
    except Exception as e:
        await message.answer(
            f"❌ Не удалось кикнуть. Возможно, у бота нет прав админа.\nОшибка: {e}"
        )
