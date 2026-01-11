import json
from services import vk, get_text, create_keyboard

keys = ["карты"]


def get_maps_keyboard():
    return create_keyboard(
        [
            [
                {
                    "action": {
                        "type": "callback",
                        "label": "Обновить",
                        "payload": json.dumps({"type": "refresh_maps"}),
                    }
                }
            ]
        ]
    )


def run(event, args):
    peer_id = event.obj.message["peer_id"]
    text = get_text("maps.php")
    vk.messages.send(
        peer_id=peer_id, message=text, keyboard=get_maps_keyboard(), random_id=0
    )


# Функция для обработки кнопки (вызывается из main.py)
def handle_callback(event):
    text = get_text("maps.php")

    vk.messages.sendMessageEventAnswer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
        event_data=json.dumps({"type": "show_snackbar", "text": "Обновлено ✅"}),
    )

    try:
        vk.messages.edit(
            peer_id=event.object.peer_id,
            conversation_message_id=event.object.conversation_message_id,
            message=text,
            keyboard=get_maps_keyboard(),
        )
    except:
        pass
