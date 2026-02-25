#!/usr/bin/env python3
"""
Sex Image Pool Manager
======================
Интерактивный скрипт для управления пулом секс-изображений.

Загружает фотки из new_sex_pics/ в MinIO через docker exec vitte_minio mc.
После загрузки обновляет SEX_IMAGE_POOL в sex_images.py.

Использование (на сервере):
  cd ~/vitte_dev_for_deploy/telegram-bot-microservices
  python3 scripts/manage_sex_pool.py

Структура new_sex_pics/:
  new_sex_pics/
    lina/
      sauna_support/
        schene_1/   ← кладёшь сюда фотки
        schene_2/
        ...
    mei/
      ...
"""

import os
import re
import sys
import subprocess

# ==================== CONFIG ====================

MINIO_CONTAINER = "vitte_minio"
MINIO_ALIAS = "local"
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "MIn!o_pASS_vitte2006_&&_pic$"
MINIO_BUCKET = "vitte-bot"
SEX_PREFIX = "sex-pics"

# Путь к new_sex_pics/ относительно скрипта (корень проекта)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_PICS_DIR = os.path.join(PROJECT_ROOT, "new_sex_pics")

# Путь к sex_images.py
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

# ==================== MC HELPERS ====================

def mc(args: list[str], capture=True) -> str:
    """Запускает mc внутри MinIO контейнера."""
    cmd = ["docker", "exec", MINIO_CONTAINER, "mc"] + args
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if capture:
        return result.stdout.strip()
    return ""


def mc_setup_alias():
    """Настраивает алиас local в mc (идемпотентно)."""
    mc(["alias", "set", MINIO_ALIAS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY])


def mc_count_files(prefix: str) -> int:
    """Считает файлы в MinIO по префиксу."""
    out = mc(["ls", f"{MINIO_ALIAS}/{MINIO_BUCKET}/{prefix}"])
    if not out:
        return 0
    lines = [l for l in out.splitlines() if l.strip() and not l.strip().endswith("/")]
    return len(lines)


def mc_copy_file(local_path: str, minio_object: str) -> bool:
    """Копирует файл в MinIO."""
    # Копируем через docker cp в контейнер, потом mc cp внутри
    tmp_path = f"/tmp/upload_{os.path.basename(local_path)}"
    # docker cp local → container:/tmp/
    cp_result = subprocess.run(
        ["docker", "cp", local_path, f"{MINIO_CONTAINER}:{tmp_path}"],
        capture_output=True, text=True
    )
    if cp_result.returncode != 0:
        print(f"  ❌ docker cp failed: {cp_result.stderr}")
        return False

    # mc cp /tmp/file → minio
    put_result = subprocess.run(
        ["docker", "exec", MINIO_CONTAINER, "mc", "cp",
         tmp_path, f"{MINIO_ALIAS}/{MINIO_BUCKET}/{minio_object}"],
        capture_output=True, text=True
    )
    # Чистим tmp
    subprocess.run(["docker", "exec", MINIO_CONTAINER, "rm", "-f", tmp_path],
                   capture_output=True)

    if put_result.returncode != 0:
        print(f"  ❌ mc cp failed: {put_result.stderr}")
        return False
    return True


# ==================== ЛОГИКА ====================

def get_story_number(persona_key: str, story_key: str) -> int | None:
    stories = STORY_ORDER_MAP.get(persona_key, [])
    try:
        return stories.index(story_key) + 1
    except ValueError:
        return None


def get_local_images(folder: str) -> list[str]:
    """Возвращает отсортированный список картинок в папке (без .gitkeep)."""
    if not os.path.isdir(folder):
        return []
    exts = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
    files = [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if os.path.splitext(f)[1] in exts
    ]
    return files


def upload_scene(persona_key: str, story_key: str, schene_key: str) -> int:
    """Загружает фотки из new_sex_pics/persona/story/schene/ в MinIO."""
    local_dir = os.path.join(NEW_PICS_DIR, persona_key, story_key, schene_key)
    local_files = get_local_images(local_dir)

    if not local_files:
        return 0

    folder = PERSONA_FOLDER_MAP[persona_key]
    story_num = get_story_number(persona_key, story_key)
    minio_prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"

    # Считаем уже загруженные
    existing = mc_count_files(minio_prefix)
    start_index = existing + 1

    print(f"    📁 {minio_prefix}")
    print(f"    Уже в MinIO: {existing}, загружаю {len(local_files)} новых (с {start_index:03d}.png)")

    uploaded = 0
    for local_path in local_files:
        filename = f"{start_index:03d}.png"
        object_name = f"{minio_prefix}{filename}"
        ok = mc_copy_file(local_path, object_name)
        if ok:
            print(f"    ✅ {os.path.basename(local_path)} → {filename}")
            start_index += 1
            uploaded += 1
        else:
            print(f"    ❌ Ошибка: {os.path.basename(local_path)}")

    return uploaded


def scan_all_pool() -> dict:
    """Сканирует MinIO и возвращает актуальный SEX_IMAGE_POOL."""
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
                cnt = mc_count_files(prefix)
                if cnt > 0:
                    story_data[schene_key] = cnt
            if story_data:
                persona_data[story_key] = story_data
        if persona_data:
            pool[persona_key] = persona_data
    return pool


def update_sex_images_py(pool: dict) -> bool:
    """Обновляет SEX_IMAGE_POOL в sex_images.py."""
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

    # Бэкап
    with open(SEX_IMAGES_PY + ".bak", "w", encoding="utf-8") as f:
        f.write(content)

    with open(SEX_IMAGES_PY, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ sex_images.py обновлён")
    return True


# ==================== СТАТУС ====================

def print_status():
    """Показывает что лежит в new_sex_pics/ — сколько новых фоток готово к загрузке."""
    print("\n" + "=" * 65)
    print("📂 НОВЫЕ ФОТО В new_sex_pics/ (готовы к загрузке)")
    print("=" * 65)
    total = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        persona_dir = os.path.join(NEW_PICS_DIR, persona_key)
        if not os.path.isdir(persona_dir):
            continue
        persona_total = 0
        rows = []
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            story_dir = os.path.join(persona_dir, story_key)
            if not os.path.isdir(story_dir):
                continue
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                schene_dir = os.path.join(story_dir, schene_key)
                cnt = len(get_local_images(schene_dir))
                if cnt > 0:
                    rows.append(f"{story_key}/{schene_key}: {cnt} фото")
                    persona_total += cnt
        if persona_total > 0:
            print(f"\n👤 {persona_key.upper()} — {persona_total} фото")
            for r in rows:
                print(f"  {r}")
        total += persona_total

    if total == 0:
        print("\n  (нет новых фото — положи картинки в new_sex_pics/персонаж/история/schene_N/)")
    else:
        print(f"\n{'=' * 65}")
        print(f"📸 Итого новых фото: {total}")
    print("=" * 65 + "\n")


def print_minio_status():
    """Показывает текущее состояние MinIO."""
    print("\n🔄 Сканирую MinIO...")
    print("=" * 65)
    print("📊 ТЕКУЩЕЕ СОСТОЯНИЕ В MINIO")
    print("=" * 65)
    total = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        folder = PERSONA_FOLDER_MAP[persona_key]
        stories = STORY_ORDER_MAP.get(persona_key, [])
        persona_total = 0
        rows = []
        for i, story_key in enumerate(stories):
            story_num = i + 1
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
                cnt = mc_count_files(prefix)
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


# ==================== ЗАГРУЗКА ====================

def upload_all():
    """Загружает ВСЁ что есть в new_sex_pics/ в MinIO."""
    total_uploaded = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        persona_dir = os.path.join(NEW_PICS_DIR, persona_key)
        if not os.path.isdir(persona_dir):
            continue
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            story_dir = os.path.join(persona_dir, story_key)
            if not os.path.isdir(story_dir):
                continue
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                schene_dir = os.path.join(story_dir, schene_key)
                local_files = get_local_images(schene_dir)
                if not local_files:
                    continue
                print(f"\n  ⬆️  {persona_key}/{story_key}/{schene_key} ({len(local_files)} фото)")
                n = upload_scene(persona_key, story_key, schene_key)
                total_uploaded += n

    return total_uploaded


# ==================== МЕНЮ ====================

def main():
    print("=" * 50)
    print("🎬 Sex Image Pool Manager")
    print("=" * 50)

    # Проверяем docker
    result = subprocess.run(["docker", "ps", "--filter", f"name={MINIO_CONTAINER}", "--format", "{{.Names}}"],
                            capture_output=True, text=True)
    if MINIO_CONTAINER not in result.stdout:
        print(f"❌ Контейнер {MINIO_CONTAINER} не найден. Запусти скрипт на сервере.")
        sys.exit(1)

    mc_setup_alias()
    print(f"✅ MinIO подключён ({MINIO_CONTAINER})")
    print(f"📁 Папка с новыми фото: {NEW_PICS_DIR}")

    while True:
        print("\n📋 МЕНЮ:")
        print("  1. Показать новые фото (готовы к загрузке из new_sex_pics/)")
        print("  2. Показать текущее состояние MinIO")
        print("  3. Загрузить ВСЁ из new_sex_pics/ в MinIO")
        print("  4. Пересканировать MinIO → обновить sex_images.py")
        print("  0. Выход")

        choice = input("\nВыбор: ").strip()

        if choice == "1":
            print_status()

        elif choice == "2":
            print_minio_status()

        elif choice == "3":
            print_status()
            confirm = input("Загрузить все новые фото в MinIO? (y/n): ").strip().lower()
            if confirm != "y":
                continue
            print("\n⬆️  Загружаю...")
            total = upload_all()
            if total > 0:
                print(f"\n✅ Загружено {total} фото")
                upd = input("Обновить SEX_IMAGE_POOL в sex_images.py? (y/n): ").strip().lower()
                if upd == "y":
                    print("🔄 Сканирую MinIO...")
                    pool = scan_all_pool()
                    update_sex_images_py(pool)
                    print("\n⚠️  Не забудь пересобрать контейнер:")
                    print("   docker compose up -d --build vitte_api vitte_bot")
            else:
                print("  Нечего загружать — нет фото в new_sex_pics/")

        elif choice == "4":
            print("🔄 Сканирую MinIO...")
            pool = scan_all_pool()
            total = sum(sum(s.values()) for stories in pool.values() for s in stories.values())
            print(f"Найдено {total} фото в {len(pool)} персонажах")
            confirm = input("Обновить sex_images.py? (y/n): ").strip().lower()
            if confirm == "y":
                update_sex_images_py(pool)
                print("\n⚠️  Не забудь пересобрать контейнер:")
                print("   docker compose up -d --build vitte_api vitte_bot")

        elif choice == "0":
            print("Выход.")
            break
        else:
            print("Неверный выбор")


if __name__ == "__main__":
    main()
