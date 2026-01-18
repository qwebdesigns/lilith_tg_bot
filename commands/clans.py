from services import get_text

keys = ["клан", "клан вк", "клан стим", "клан херо"]

PERMISSIONS = {
    "клан": "clan_all",
    "клан стим": "clan_steam",
    "клан херо": "clan_hero",
    "клан вкплей": "clan_all",
    "клан вк плей": "clan_all",
    "клан вк": "clan_all",
    "клан майл": "clan_all",
    "клан окру": "clan_all",
    "клан ок": "clan_all",
}

async def run(message, args, bot):
    cmd = message.text.lower()

    resp = ""
    if "клан вк плей" in cmd:
        resp = await get_text("clan_vk_play.php")
    elif "клан вкплей" in cmd:
        resp = await get_text("clan_vk_play.php")
    elif "клан стим" in cmd:
        resp = await get_text("clan_steam.php")
    elif "клан херо" in cmd:
        resp = await get_text("clan_steam_t1.php")
    elif "клан окру" in cmd:
        resp = await get_text("clan_okru.php")
    elif "клан ок" in cmd:
        resp = await get_text("clan_okru.php")
    elif "клан вк" in cmd:
        resp = await get_text("clan.php")
    elif "клан майл" in cmd:
        resp = await get_text("clan_mail.php")
    else:
        # Просто "клан"
        resp = await get_text("clan_all.php")

    await message.answer(resp)
