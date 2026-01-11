from services import vk, extract_mention, get_text

keys = ["айди", "участник"]


def run(event, args):
    text = event.obj.message["text"].lower()
    peer_id = event.obj.message["peer_id"]
    user_id = event.obj.message["from_id"]

    # Команда АЙДИ
    if "айди" in text:
        target = user_id
        if args:
            found = extract_mention(args)
            if found:
                target = found
        vk.messages.send(peer_id=peer_id, message=f"VK ID: {target}", random_id=0)

    # Команда УЧАСТНИК
    elif "участник" in text:
        target = args if args else user_id
        info = get_text(f"player_get_bot.php?link={target}")
        vk.messages.send(peer_id=peer_id, message=info, random_id=0)
