from services import add_ban, remove_ban

keys = ["бан", "разбан"]

PERMISSIONS = {
    "бан": "ban",
    "разбан": "unban"
    }


async def run(message, args, bot):
    chat_id = message.chat.id
    text = message.text.lower()

    # --- ЛОГИКА РАЗБАНА ---
    if "разбан" in text or "unban" in text:
        # Пытаемся найти ID
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        # Если передан аргумент (числовой ID)
        elif args and args.isdigit():
            target_id = int(args)

        if target_id:
            if remove_ban(chat_id, target_id):
                # Также снимаем бан в самом телеграме
                try:
                    await bot.unban_chat_member(chat_id, target_id)
                except:
                    pass
                await message.answer(
                    f"✅ Пользователь {target_id} удален из базы банов."
                )
            else:
                await message.answer(
                    "Этого пользователя нет в локальном черном списке."
                )
        else:
            await message.answer(
                "Кого разбанить? Ответьте на сообщение или укажите ID."
            )
        return

    # --- ЛОГИКА БАНА ---
    target_id = None
    target_name = "Пользователь"

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name

    if not target_id:
        await message.answer("⛔ Ответьте на сообщение пользователя для бана.")
        return

    # 1. Заносим в базу (чтобы авто-кикать при возвращении)
    add_ban(chat_id, target_id)

    # 2. Баним в Телеграме
    try:
        await bot.ban_chat_member(chat_id, target_id)
        await message.answer(
            f"⛔ {target_name} (ID: {target_id}) забанен и внесен в черный список."
        )
    except Exception as e:
        await message.answer(
            f"⚠️ В базу добавил, но кикнуть не смог (нет прав?).\nОшибка: {e}"
        )
