from services import get_text

keys = ["клан", "клан вк", "клан стим", "клан херо"]

PERMISSIONS = {
    "клан": 'clan_all',
    "клан вк": 'clan_vk',
    "клан стим": 'clan_steam',
    "клан херо": 'clan_hero'
}

async def run(message, args, bot):
    cmd = message.text.lower()

    resp = ""
    if "клан вк" in cmd:
        resp = await get_text("clan.php")
    elif "клан стим" in cmd:
        resp = await get_text("clan_steam.php")
    elif "клан херо" in cmd:
        resp = await get_text("clan_steam_t1.php")
    else:
        # Просто "клан"
        resp = await get_text("clan_all.php")

    await message.answer(resp)
