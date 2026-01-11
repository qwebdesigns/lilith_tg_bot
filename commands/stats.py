from services import vk, get_text

keys = ["топ", "профили"]


def run(event, args):
    peer_id = event.obj.message["peer_id"]
    cmd = event.obj.message["text"].lower()

    if "топ" in cmd:
        resp = get_text("stat_per_week.php")
    else:
        resp = get_text("players_ID.php")

    vk.messages.send(peer_id=peer_id, message=resp, random_id=0)
