#!/usr/bin/env python3
"""
Sex Image Pool Manager
======================
Запускается ЛОКАЛЬНО. Подключается к MinIO на сервере через SSH-туннель.

Установка (один раз):
  pip install minio sshpass   # sshpass через brew на Mac: brew install hudochenkov/sshpass/sshpass
  # или просто: pip install minio

Использование:
  cd telegram-bot-microservices
  python3 scripts/manage_sex_pool.py

Структура new_sex_pics/:
  new_sex_pics/lina/sauna_support/schene_1/  ← кладёшь сюда фотки
"""

import os
import re
import sys
import time
import glob
import signal
import subprocess
import threading

# ==================== SSH / MINIO CONFIG ====================

SSH_HOST = "212.118.52.137"
SSH_USER = "root"
SSH_PASSWORD = "z4wBLit95x3ty-4P6r5u"
SSH_PORT = 22

# Локальный порт для туннеля
TUNNEL_LOCAL_PORT = 19000
# MinIO внутри сервера
MINIO_REMOTE_HOST = "localhost"
MINIO_REMOTE_PORT = 9000

MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "MIn!o_pASS_vitte2006_&&_pic$"
MINIO_BUCKET = "vitte-bot"
SEX_PREFIX = "sex-pics"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_PICS_DIR = os.path.join(PROJECT_ROOT, "new_sex_pics")
SEX_IMAGES_PY = os.path.join(PROJECT_ROOT, "shared", "llm", "services", "sex_images.py")

# ==================== МАППИНГИ ====================

PERSONA_FOLDER_MAP = {
    "lina": "lina_sex",
    "mei": "mei_sex",
    "julie": "julie_sex",
    "hani": "honney_sex",
    "pai": "pai_sex",
    "ash": "ash_sex",
    "anastasia": "anastasia_sex",
    "sasha": "sasha_sex",
    "yuna": "una_sex",
    "roxy": "roxy_sex",
    "marianna": "marriana_sex",
    "stacey": "stacy_sex",
}

STORY_ORDER_MAP = {
    "lina": ["sauna_support", "shower_flirt", "gym_late", "competition_prep"],
    "mei": ["mall_bench", "car_ride", "home_visit", "regular_visits"],
    "julie": ["home_tutor", "teacher_punishment", "bus_fun"],
    "hani": ["photoshoot", "pool", "elevator"],
    "pai": ["dinner", "window", "car"],
    "ash": ["living_room", "bedroom"],
    "anastasia": ["classroom", "bathroom"],
    "sasha": ["auction", "plane", "party"],
    "yuna": ["city_lights", "first_evening", "tea_secrets"],
    "roxy": ["hitchhiker", "maid", "beach"],
    "marianna": ["support", "cozy", "flirt", "serious"],
    "stacey": ["rooftop_sunset", "hints_game", "night_park", "confession"],
}

SCENE_MAP = {
    "missionary": 1,
    "doggy": 2,
    "cowgirl": 3,
    "reverse_cowgirl": 4,
    "standing_behind": 5,
    "prone_bone": 6,
    "mating_press": 8,
    "arched_doggy": 9,
    "reverse_lean": 10,
}

# ==================== SSH TUNNEL ====================

_tunnel_proc = None


def start_ssh_tunnel() -> bool:
    """Поднимает SSH-туннель localhost:19000 → сервер:9000."""
    global _tunnel_proc

    # Проверяем sshpass
    if subprocess.run(["which", "sshpass"], capture_output=True).returncode != 0:
        print("❌ sshpass не найден.")
        print("   Mac: brew install hudochenkov/sshpass/sshpass")
        print("   Linux: apt install sshpass")
        return False

    cmd = [
        "sshpass", "-p", SSH_PASSWORD,
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-N",  # не выполнять команды, только туннель
        "-L", f"{TUNNEL_LOCAL_PORT}:{MINIO_REMOTE_HOST}:{MINIO_REMOTE_PORT}",
        f"{SSH_USER}@{SSH_HOST}",
        "-p", str(SSH_PORT),
    ]

    _tunnel_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Ждём пока туннель поднимется
    for _ in range(10):
        time.sleep(0.5)
        if _tunnel_proc.poll() is not None:
            print(f"❌ SSH туннель не запустился (код {_tunnel_proc.returncode})")
            return False
        # Проверяем что порт открылся
        import socket
        try:
            with socket.create_connection(("localhost", TUNNEL_LOCAL_PORT), timeout=1):
                return True
        except OSError:
            continue

    print("❌ SSH туннель не ответил за 5 секунд")
    return False


def stop_ssh_tunnel():
    global _tunnel_proc
    if _tunnel_proc and _tunnel_proc.poll() is None:
        _tunnel_proc.terminate()
        _tunnel_proc = None


# ==================== MINIO ====================

def get_client():
    try:
        from minio import Minio
    except ImportError:
        print("❌ minio не установлен: pip install minio")
        sys.exit(1)
    return Minio(
        f"localhost:{TUNNEL_LOCAL_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def count_files(client, prefix: str) -> int:
    try:
        objects = list(client.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True))
        return len([o for o in objects if not o.object_name.endswith("/")])
    except Exception:
        return 0


# ==================== ЛОГИКА ====================

def get_story_number(persona_key: str, story_key: str):
    stories = STORY_ORDER_MAP.get(persona_key, [])
    try:
        return stories.index(story_key) + 1
    except ValueError:
        return None


def get_local_images(folder: str) -> list:
    if not os.path.isdir(folder):
        return []
    exts = {".jpg", ".jpeg", ".png"}
    files = [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if os.path.splitext(f)[1].lower() in exts
    ]
    return files


def upload_scene(client, persona_key: str, story_key: str, schene_key: str) -> int:
    local_dir = os.path.join(NEW_PICS_DIR, persona_key, story_key, schene_key)
    local_files = get_local_images(local_dir)
    if not local_files:
        return 0

    folder = PERSONA_FOLDER_MAP[persona_key]
    story_num = get_story_number(persona_key, story_key)
    minio_prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"

    existing = count_files(client, minio_prefix)
    start_index = existing + 1

    print(f"    📁 {minio_prefix}")
    print(f"    В MinIO: {existing}, загружаю {len(local_files)} новых (с {start_index:03d}.png)")

    uploaded = 0
    for local_path in local_files:
        filename = f"{start_index:03d}.png"
        object_name = f"{minio_prefix}{filename}"
        try:
            client.fput_object(MINIO_BUCKET, object_name, local_path, content_type="image/png")
            print(f"    ✅ {os.path.basename(local_path)} → {filename}")
            start_index += 1
            uploaded += 1
        except Exception as e:
            print(f"    ❌ {os.path.basename(local_path)}: {e}")

    return uploaded


def scan_all_pool(client) -> dict:
    pool = {}
    for persona_key, folder in PERSONA_FOLDER_MAP.items():
        stories = STORY_ORDER_MAP.get(persona_key, [])
        persona_data = {}
        for i, story_key in enumerate(stories):
            story_num = i + 1
            story_data = {}
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
                cnt = count_files(client, prefix)
                if cnt > 0:
                    story_data[schene_key] = cnt
            if story_data:
                persona_data[story_key] = story_data
        if persona_data:
            pool[persona_key] = persona_data
    return pool


def update_sex_images_py(pool: dict) -> bool:
    if not os.path.exists(SEX_IMAGES_PY):
        print(f"❌ Файл не найден: {SEX_IMAGES_PY}")
        return False

    with open(SEX_IMAGES_PY, "r", encoding="utf-8") as f:
        content = f.read()

    lines = ["SEX_IMAGE_POOL = {\n"]
    for persona_key in sorted(pool.keys()):
        persona_data = pool[persona_key]
        lines.append(f'    "{persona_key}": {{\n')
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            if story_key not in persona_data:
                continue
            story_data = persona_data[story_key]
            sorted_scenes = dict(sorted(story_data.items(), key=lambda x: int(x[0].split("_")[1])))
            scene_str = ", ".join(f'"{k}": {v}' for k, v in sorted_scenes.items())
            lines.append(f'        "{story_key}": {{{scene_str}}},\n')
        lines.append("    },\n")
    lines.append("    # taya: no sex images yet\n")
    lines.append("}\n")
    new_pool_block = "".join(lines)

    pattern = r"SEX_IMAGE_POOL\s*=\s*\{.*?(?=\n# MinIO base path|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("❌ Не нашёл блок SEX_IMAGE_POOL в файле")
        return False

    new_content = content[:match.start()] + new_pool_block + "\n" + content[match.end():]

    with open(SEX_IMAGES_PY + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    with open(SEX_IMAGES_PY, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ sex_images.py обновлён (бэкап: sex_images.py.bak)")
    return True


# ==================== СТАТУС ====================

def print_local_status():
    print("\n" + "=" * 65)
    print("📂 НОВЫЕ ФОТО В new_sex_pics/ (готовы к загрузке)")
    print("=" * 65)
    total = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        persona_dir = os.path.join(NEW_PICS_DIR, persona_key)
        if not os.path.isdir(persona_dir):
            continue
        rows = []
        persona_total = 0
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                schene_dir = os.path.join(persona_dir, story_key, schene_key)
                cnt = len(get_local_images(schene_dir))
                if cnt > 0:
                    rows.append(f"  {story_key}/{schene_key}: {cnt} фото")
                    persona_total += cnt
        if persona_total > 0:
            print(f"\n👤 {persona_key.upper()} — {persona_total} фото")
            for r in rows:
                print(r)
        total += persona_total

    if total == 0:
        print("\n  (пусто — положи фотки в new_sex_pics/персонаж/история/schene_N/)")
    else:
        print(f"\n{'=' * 65}")
        print(f"📸 Итого новых фото: {total}")
    print("=" * 65 + "\n")


def print_minio_status(client):
    print("\n🔄 Сканирую MinIO...")
    print("=" * 65)
    print("📊 СОСТОЯНИЕ В MINIO")
    print("=" * 65)
    total = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        folder = PERSONA_FOLDER_MAP[persona_key]
        stories = STORY_ORDER_MAP.get(persona_key, [])
        rows = []
        persona_total = 0
        for i, story_key in enumerate(stories):
            story_num = i + 1
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
                cnt = count_files(client, prefix)
                if cnt > 0:
                    rows.append(f"  story_{story_num}({story_key})/{schene_key}: {cnt}")
                    persona_total += cnt
        if persona_total > 0:
            print(f"\n👤 {persona_key.upper()} — {persona_total} фото")
            for r in rows:
                print(r)
        total += persona_total
    print(f"\n{'=' * 65}")
    print(f"📸 ВСЕГО В MINIO: {total} фото")
    print("=" * 65 + "\n")


def upload_all(client) -> int:
    total = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        persona_dir = os.path.join(NEW_PICS_DIR, persona_key)
        if not os.path.isdir(persona_dir):
            continue
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                schene_dir = os.path.join(persona_dir, story_key, schene_key)
                if not get_local_images(schene_dir):
                    continue
                print(f"\n  ⬆️  {persona_key}/{story_key}/{schene_key}")
                n = upload_scene(client, persona_key, story_key, schene_key)
                total += n
    return total


# ==================== MAIN ====================

def main():
    print("=" * 55)
    print("🎬 Sex Image Pool Manager")
    print(f"   Сервер: {SSH_HOST}")
    print(f"   Папка:  {NEW_PICS_DIR}")
    print("=" * 55)

    # Проверяем minio SDK
    try:
        import minio
    except ImportError:
        print("❌ Установи зависимость: pip install minio")
        sys.exit(1)

    print(f"\n🔌 Поднимаю SSH-туннель → {SSH_HOST}:{MINIO_REMOTE_PORT}...")
    if not start_ssh_tunnel():
        sys.exit(1)
    print(f"✅ Туннель готов (localhost:{TUNNEL_LOCAL_PORT})")

    # Закрываем туннель при выходе
    signal.signal(signal.SIGINT, lambda s, f: (stop_ssh_tunnel(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (stop_ssh_tunnel(), sys.exit(0)))

    try:
        client = get_client()
        # Проверяем подключение
        client.bucket_exists(MINIO_BUCKET)
        print("✅ MinIO подключён\n")
    except Exception as e:
        print(f"❌ MinIO недоступен: {e}")
        stop_ssh_tunnel()
        sys.exit(1)

    while True:
        print("📋 МЕНЮ:")
        print("  1. Показать новые фото (из new_sex_pics/)")
        print("  2. Показать состояние MinIO")
        print("  3. Загрузить всё из new_sex_pics/ в MinIO")
        print("  4. Пересканировать MinIO → обновить sex_images.py")
        print("  0. Выход")

        choice = input("\nВыбор: ").strip()

        if choice == "1":
            print_local_status()

        elif choice == "2":
            print_minio_status(client)

        elif choice == "3":
            print_local_status()
            confirm = input("Загрузить всё в MinIO? (y/n): ").strip().lower()
            if confirm != "y":
                continue
            total = upload_all(client)
            if total > 0:
                print(f"\n✅ Загружено {total} фото")
                upd = input("Обновить SEX_IMAGE_POOL в sex_images.py? (y/n): ").strip().lower()
                if upd == "y":
                    print("🔄 Сканирую MinIO...")
                    pool = scan_all_pool(client)
                    update_sex_images_py(pool)
                    print("\n⚠️  Задеплой изменения на сервер:")
                    print("   git add shared/llm/services/sex_images.py && git commit -m 'update sex pool'")
                    print("   git push  →  на сервере: git pull && docker compose up -d --build vitte_api vitte_bot")
            else:
                print("  Нечего загружать")

        elif choice == "4":
            print("🔄 Сканирую MinIO...")
            pool = scan_all_pool(client)
            total = sum(sum(s.values()) for stories in pool.values() for s in stories.values())
            print(f"Найдено {total} фото в {len(pool)} персонажах")
            confirm = input("Обновить sex_images.py? (y/n): ").strip().lower()
            if confirm == "y":
                update_sex_images_py(pool)

        elif choice == "0":
            break
        else:
            print("Неверный выбор\n")

    stop_ssh_tunnel()
    print("Выход.")


if __name__ == "__main__":
    main()
