from services import get_text

keys = ["топ", "профили"]

PERMISSIONS = {
    "топ": 'stat_per_week',
    "профили": 'players_ID'
    }

async def run(message, args, bot):
    cmd = message.text.lower()

    if "топ" in cmd:
        resp = await get_text("stat_per_week.php")
    else:
        resp = await get_text("players_ID.php")

    await message.answer(resp)
