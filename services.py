import vk_api
import requests
import re
import json
import os  # <--- Вот это потерялось
import time  # <--- И это нужно для времени мута
from urllib.parse import quote
from config import TOKEN, BASE_URL

# --- АВТОРИЗАЦИЯ ВК ---
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
upload = vk_api.VkUpload(vk_session)  # Для загрузки фото

# Отключаем ошибки SSL
requests.packages.urllib3.disable_warnings()


# --- ФУНКЦИИ API ---
def get_text(endpoint):
    """Простой GET запрос"""
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", verify=False)
        return r.text
    except Exception as e:
        return f"Ошибка API: {e}"


def search_weapon(alias, mode="weapons.php"):
    """Поиск оружия (ТТХ или ТТК)"""
    encoded = quote(alias.strip().encode("utf-8"))
    try:
        r = requests.get(f"{BASE_URL}{mode}?alias={encoded}", verify=False)
        return r.text.strip()
    except Exception as e:
        return f"Ошибка: {e}"


def download_image():
    """Скачивание картинки результата"""
    url = "https://gammahub.tech/lilit_bot/assets/temp/result.png"
    try:
        r = requests.get(url, verify=False)
        if r.status_code == 200:
            return r.content
    except:
        return None


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def extract_mention(text):
    """Вытаскивает ID из [id1|User]"""
    if not text:
        return None
    mention = re.findall(r"\[id(\d+)\|.*?\]|@(\w+)", text)
    if mention:
        return mention[0][0] or mention[0][1]
    return None


def extract_weapon_list(text):
    """Парсит список оружий если поиск не дал точного результата"""
    if not text.startswith("Нет результатов"):
        return []
    lines = text.replace("<br>", "\n").split("\n")
    weapons = []
    for line in lines:
        if line.strip().startswith("- "):
            weapons.append(line.strip()[2:].strip())
    return weapons


def create_keyboard(buttons_data):
    """Упрощенное создание клавиатуры"""
    return json.dumps({"inline": True, "buttons": buttons_data})


MUTE_FILE = "mutes.json"


def load_mutes():
    if not os.path.exists(MUTE_FILE):
        return {}
    try:
        with open(MUTE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_mutes(data):
    with open(MUTE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def add_mute(peer_id, user_id, duration_seconds):
    """Добавляет пользователя в мут"""
    db = load_mutes()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id not in db:
        db[peer_id] = {}

    # Вычисляем время окончания мута
    end_time = int(time.time()) + duration_seconds
    db[peer_id][user_id] = end_time
    save_mutes(db)


def remove_mute(peer_id, user_id):
    """Снимает мут"""
    db = load_mutes()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id in db and user_id in db[peer_id]:
        del db[peer_id][user_id]
        save_mutes(db)
        return True
    return False


def check_mute(peer_id, user_id):
    """
    Проверяет, в муте ли пользователь.
    Возвращает True, если надо удалить сообщение.
    """
    db = load_mutes()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id in db and user_id in db[peer_id]:
        end_time = db[peer_id][user_id]

        # Если время мута вышло — удаляем из базы и разрешаем писать
        if int(time.time()) > end_time:
            del db[peer_id][user_id]
            save_mutes(db)
            return False

        return True  # Пользователь все еще в муте
    return False


BANS_FILE = "bans.json"


def load_bans():
    if not os.path.exists(BANS_FILE):
        return {}
    try:
        with open(BANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_bans(data):
    with open(BANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def add_ban(peer_id, user_id):
    """Добавляет пользователя в вечный бан"""
    db = load_bans()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id not in db:
        db[peer_id] = []

    if user_id not in db[peer_id]:
        db[peer_id].append(user_id)
        save_bans(db)


def remove_ban(peer_id, user_id):
    """Снимает бан"""
    db = load_bans()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id in db and user_id in db[peer_id]:
        db[peer_id].remove(user_id)
        save_bans(db)
        return True
    return False


def check_is_banned(peer_id, user_id):
    """Проверяет, забанен ли юзер"""
    db = load_bans()
    peer_id = str(peer_id)
    user_id = str(user_id)

    if peer_id in db and user_id in db[peer_id]:
        return True
    return False
