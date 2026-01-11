import json
from services import (
    vk,
    upload,
    search_weapon,
    download_image,
    extract_weapon_list,
    create_keyboard,
)

keys = ["ттх", "ттк", "о"]


def run(event, args):
    peer_id = event.obj.message["peer_id"]
    cmd_text = event.obj.message["text"].lower()

    # Определяем режим
    mode = "weapons.php"
    if "ттк" in cmd_text:
        mode = "weapons_ttk.php"

    if not args:
        vk.messages.send(
            peer_id=peer_id, message="Укажите название оружия", random_id=0
        )
        return

    process_weapon(peer_id, args, mode)


def process_weapon(
    peer_id, weapon_name, mode="weapons.php", event_id=None, user_id=None
):
    # Уведомление
    if event_id:
        vk.messages.sendMessageEventAnswer(
            event_id=event_id,
            user_id=user_id,
            peer_id=peer_id,
            event_data=json.dumps({"type": "show_snackbar", "text": "Генерирую..."}),
        )
    else:
        if mode == "weapons.php":  # Для ТТК обычно только текст, для ТТХ фото
            vk.messages.send(
                peer_id=peer_id, message="Генерирую фоточку🥰", random_id=0
            )

    # Запрос
    resp = search_weapon(weapon_name, mode)

    # 1. Если картинка
    if resp == "1":
        img = download_image()
        if img:
            with open("temp.png", "wb") as f:
                f.write(img)
            photo = upload.photo_messages("temp.png")[0]
            att = f"photo{photo['owner_id']}_{photo['id']}"
            vk.messages.send(peer_id=peer_id, attachment=att, random_id=0)
        else:
            vk.messages.send(peer_id=peer_id, message="Ошибка фото", random_id=0)

    # 2. Если список вариантов
    elif "Нет результатов" in resp:
        variants = extract_weapon_list(resp)
        if variants and mode == "weapons.php":
            buttons = []
            for w in variants[:10]:
                buttons.append(
                    [
                        {
                            "action": {
                                "type": "callback",
                                "label": w[:40],
                                "payload": json.dumps(
                                    {"type": "select_weapon", "weapon": w}
                                ),
                            }
                        }
                    ]
                )
            kb = create_keyboard(buttons)
            vk.messages.send(peer_id=peer_id, message=resp, keyboard=kb, random_id=0)
        else:
            vk.messages.send(peer_id=peer_id, message=resp, random_id=0)

    # 3. Текст
    else:
        vk.messages.send(peer_id=peer_id, message=resp, random_id=0)


# Обработка кнопки
def handle_callback(event):
    weapon = event.object.payload.get("weapon")
    process_weapon(
        peer_id=event.object.peer_id,
        weapon_name=weapon,
        event_id=event.object.event_id,
        user_id=event.object.user_id,
    )
