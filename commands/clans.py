from services import vk, get_text

keys = ["клан", "клан вк", "клан стим", "клан херо"]


def run(event, args):
    cmd = event.obj.message[
        "text"
    ].lower()  # Получаем полный текст, чтобы понять нюансы
    peer_id = event.obj.message["peer_id"]

    resp = ""
    if "клан вк" in cmd:
        resp = get_text("clan.php")
    elif "клан стим" in cmd:
        resp = get_text("clan_steam.php")
    elif "клан херо" in cmd:
        resp = get_text("clan_steam_t1.php")
    else:
        # Просто "клан"
        resp = get_text("clan_all.php")

    vk.messages.send(peer_id=peer_id, message=resp, random_id=0)
