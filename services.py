import json
import os
import re
import time
import aiohttp
from config import BASE_URL, ADMIN_ID

# Файл для кэша
PERMISSIONS_FILE = "permissions_cache.json"
CACHE_TTL = 60  # Время жизни кэша в секундах

# --- РАБОТА С ФАЙЛОМ КЭША ---


def load_permissions_file():
    """Читает кэш из файла"""
    if not os.path.exists(PERMISSIONS_FILE):
        return {"last_update": 0, "users": {}}
    try:
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка чтения кэша: {e}")
        return {"last_update": 0, "users": {}}


def save_permissions_file(data):
    """Сохраняет кэш в файл"""
    try:
        with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)  # indent=4 убрал для экономии места
    except Exception as e:
        print(f"Ошибка записи кэша: {e}")


# --- ОБНОВЛЕНИЕ ДАННЫХ ---


async def fetch_and_update_cache():
    """Загружает JSON с сервера и сохраняет в файл"""
    url = f"{BASE_URL}services/api_users_json.php"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status != 200:
                    print(f"Ошибка API прав: {resp.status}")
                    return None

                data = await resp.json()

                # Формируем структуру для сохранения
                # { "user_id": ["perm1", "perm2"] }
                users_perms = {}

                for role in data:
                    perms_str = role.get("permissions", "")
                    # Разбиваем строку "ban\kick" на список
                    perms_list = [p for p in perms_str.split("\\") if p]

                    for user in role.get("users", []):
                        uid = str(user.get("user_id"))
                        users_perms[uid] = perms_list

                # Итоговый объект кэша
                cache_data = {"last_update": int(time.time()), "users": users_perms}

                save_permissions_file(cache_data)
                return cache_data

    except Exception as e:
        print(f"Ошибка обновления кэша с сервера: {e}")
        return None


# --- ГЛАВНАЯ ФУНКЦИЯ ПРОВЕРКИ ---


async def check_permissions(message, required_perms, bot=None):
    """
    Проверяет права, используя файловый кэш.
    required_perms: строка или список
    """
    # 0. Если права не требуются
    if not required_perms:
        return True

    user_id = str(message.from_user.id)

    # 1. Создатель бота (Бог)
    if int(user_id) == ADMIN_ID:
        return True

    # 2. Загружаем кэш из файла
    cache = load_permissions_file()

    # 3. Проверяем актуальность (TTL)
    last_update = cache.get("last_update", 0)
    if time.time() - last_update > CACHE_TTL:
        # Кэш протух, обновляем
        new_cache = await fetch_and_update_cache()
        if new_cache:
            cache = new_cache  # Используем свежие данные

    # 4. Получаем права пользователя
    user_perms = cache.get("users", {}).get(user_id, [])

    # 5. Сравниваем (Логика: нужно хотя бы одно совпадение)
    if isinstance(required_perms, str):
        return required_perms in user_perms

    for req in required_perms:
        if req in user_perms:
            return True

    return False


async def get_text(endpoint):
    """Асинхронный GET запрос к PHP скриптам"""
    url = f"{BASE_URL}{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            # ssl=False аналог verify=False
            async with session.get(url, ssl=False) as resp:
                text = await resp.text()
                if "<br>" in text:
                    text = text.replace("<br>", "\n")
                return text
        except Exception as e:
            return f"Ошибка API: {e}"


async def search_weapon(alias, mode="weapons.php"):
    """Поиск оружия (ТТХ или ТТК)"""
    url = f"{BASE_URL}{mode}"
    params = {"alias": alias.strip()}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, ssl=False) as resp:
                return (await resp.text()).strip()
        except Exception as e:
            return f"Ошибка: {e}"


async def download_image():
    """Скачивание картинки результата (возвращает байты)"""
    url = "https://gammahub.tech/lilit_bot/assets/temp/result.png"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.read()  # Возвращаем байты, а не сохраняем сразу
        except:
            return None


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---


def extract_mention(text):
    """
    Пытается найти username или ID в тексте.
    В ТГ нет жесткого формата [id|Name], поэтому ищем @username.
    """
    if not text:
        return None

    # Ищем @username
    match = re.search(r"@(\w+)", text)
    if match:
        return match.group(1)  # Возвращаем username без @

    return None


def extract_weapon_list(text):
    """Парсит список оружий (без изменений)"""
    if not text.startswith("Нет результатов"):
        return []
    lines = text.replace("<br>", "\n").split("\n")
    weapons = []
    for line in lines:
        if line.strip().startswith("- "):
            weapons.append(line.strip()[2:].strip())
    return weapons


# --- БАЗА ДАННЫХ (JSON) ---
# Логика остается прежней: сохраняем ID чата и юзера

MUTE_FILE = "mutes.json"
BANS_FILE = "bans.json"


def load_json(filename):
    if not os.path.exists(filename):
        # Для банов список, для мутов словарь — структура из старого кода
        return {} if filename == MUTE_FILE else {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {} if filename == MUTE_FILE else {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- МУТЫ ---


def add_mute(chat_id, user_id, duration_seconds, mute_type="all"):
    """
    Добавляет мут.
    mute_type: "all", "photo", "video", "animation", "sticker", "media"
    """
    db = load_json(MUTE_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid not in db:
        db[cid] = {}

    end_time = int(time.time()) + duration_seconds

    # Сохраняем словарь: время и тип
    db[cid][uid] = {"time": end_time, "type": mute_type}
    save_json(MUTE_FILE, db)


def remove_mute(chat_id, user_id):
    db = load_json(MUTE_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid in db and uid in db[cid]:
        del db[cid][uid]
        save_json(MUTE_FILE, db)
        return True
    return False


def check_mute(chat_id, user_id):
    """
    Возвращает ТИП мута (str) или None, если мута нет.
    """
    db = load_json(MUTE_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid in db and uid in db[cid]:
        data = db[cid][uid]

        # Поддержка старого формата (если в базе число)
        if isinstance(data, int):
            end_time = data
            mute_type = "all"
        else:
            end_time = data.get("time", 0)
            mute_type = data.get("type", "all")

        # Если время вышло
        if int(time.time()) > end_time:
            del db[cid][uid]
            save_json(MUTE_FILE, db)
            return None

        return mute_type  # Возвращаем строку ("all", "photo"...)

    return None


# ... (остальные функции api_save_user и т.д.) ...
# --- БАНЫ ---


def add_ban(chat_id, user_id):
    db = load_json(BANS_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid not in db:
        db[cid] = []
    if uid not in db[cid]:
        db[cid].append(uid)
        save_json(BANS_FILE, db)


def remove_ban(chat_id, user_id):
    db = load_json(BANS_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid in db and uid in db[cid]:
        db[cid].remove(uid)
        save_json(BANS_FILE, db)
        return True
    return False


def check_is_banned(chat_id, user_id):
    db = load_json(BANS_FILE)
    cid, uid = str(chat_id), str(user_id)

    if cid in db and uid in db[cid]:
        return True
    return False


async def api_save_user(data):
    """
    Отправляет POST запрос на services/api_save_user.php
    data: dict с полями user_id, name, user_name, game_name, и т.д.
    """
    url = f"{BASE_URL}services/api_save_user.php"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=data, ssl=False) as resp:
                # Пытаемся распарсить JSON ответ от PHP
                try:
                    return await resp.json()
                except:
                    # Если PHP вернул ошибку текстом или HTML (fatal error)
                    text = await resp.text()
                    return {
                        "status": "error",
                        "message": f"Server response: {text[:200]}",
                    }
        except Exception as e:
            return {"status": "error", "message": f"Request failed: {e}"}


async def get_json(endpoint):
    """Асинхронный GET запрос, ожидающий JSON ответ"""
    url = f"{BASE_URL}{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"Ошибка JSON API: {e}")
            return None


async def api_add_tg_list(username):
    """Добавляет username в таблицу tg_list"""
    url = f"{BASE_URL}services/api_add_tg_list.php"
    data = {"username": username}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=data, ssl=False) as resp:
                return await resp.json()
        except:
            return None


# В САМЫЙ КОНЕЦ services.py ДОБАВЬТЕ ЭТО (чтобы не было ошибки import):
import asyncio

CHAT_USERS_FILE = "chat_users.json"
chat_users_lock = asyncio.Lock()


async def update_local_user(user_id, username, full_name):
    user_id = str(user_id)
    async with chat_users_lock:
        if os.path.exists(CHAT_USERS_FILE):
            try:
                with open(CHAT_USERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except:
                data = {}
        else:
            data = {}
        data[user_id] = {"username": username, "name": full_name}
        with open(CHAT_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
