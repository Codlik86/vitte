#!/usr/bin/env python3
"""
Sex Image Pool Manager
======================
Интерактивный скрипт для управления пулом секс-изображений в MinIO.

Возможности:
  1. Показать текущее состояние пула (сколько фоток по каждой позе)
  2. Загрузить новые фотки в нужную папку (с автонумерацией)
  3. Пересканировать MinIO и обновить SEX_IMAGE_POOL в sex_images.py

Использование:
  python3 scripts/manage_sex_pool.py

Требования (на сервере):
  pip install minio
"""

import os
import re
import sys
import glob

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("Установи minio: pip install minio")
    sys.exit(1)

# ==================== CONFIG ====================

MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "MIn!o_pASS_vitte2006_&&_pic$"
MINIO_BUCKET = "vitte-bot"
SEX_PREFIX = "sex-pics"

# Путь к файлу sex_images.py относительно скрипта
SEX_IMAGES_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "shared", "llm", "services", "sex_images.py"
)

# Копия маппингов из sex_images.py (для интерактивного меню)
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
    "taya": "taya_sex",
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
    "taya": ["bar_back_exit", "gaming_center", "friends_wife", "office_elevator"],
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

SCENE_NAMES_RU = {
    "missionary": "missionary (миссионерская)",
    "doggy": "doggy (сзади)",
    "cowgirl": "cowgirl (сверху)",
    "reverse_cowgirl": "reverse_cowgirl (обратная сверху)",
    "standing_behind": "standing_behind (стоя сзади)",
    "prone_bone": "prone_bone (лёжа на животе)",
    "mating_press": "mating_press (mating press)",
    "arched_doggy": "arched_doggy (arched doggy)",
    "reverse_lean": "reverse_lean (reverse lean)",
}

# ==================== MINIO ====================

def get_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def count_files_in_path(client: Minio, prefix: str) -> int:
    """Считает количество файлов в MinIO по префиксу."""
    try:
        objects = list(client.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True))
        return len([o for o in objects if not o.object_name.endswith("/")])
    except S3Error:
        return 0


def get_existing_file_count(client: Minio, persona_key: str, story_key: str, schene_key: str) -> int:
    """Возвращает текущее количество фоток в конкретной папке."""
    folder = PERSONA_FOLDER_MAP.get(persona_key)
    if not folder:
        return 0
    stories = STORY_ORDER_MAP.get(persona_key, [])
    try:
        story_num = stories.index(story_key) + 1
    except ValueError:
        return 0
    prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
    return count_files_in_path(client, prefix)


def scan_all_pool(client: Minio) -> dict:
    """Сканирует всю структуру MinIO и возвращает актуальный пул."""
    pool = {}
    for persona_key, folder in PERSONA_FOLDER_MAP.items():
        if persona_key == "taya":
            continue
        stories = STORY_ORDER_MAP.get(persona_key, [])
        persona_data = {}
        for i, story_key in enumerate(stories):
            story_num = i + 1
            story_data = {}
            # Сканируем все возможные schene_N (1-10)
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
                cnt = count_files_in_path(client, prefix)
                if cnt > 0:
                    story_data[schene_key] = cnt
            if story_data:
                persona_data[story_key] = story_data
        if persona_data:
            pool[persona_key] = persona_data
    return pool


def upload_images(client: Minio, local_dir: str, persona_key: str, story_key: str, schene_key: str) -> int:
    """
    Загружает все .jpg/.png из local_dir в MinIO.
    Нумерация продолжается с последнего существующего файла.
    Возвращает количество загруженных файлов.
    """
    folder = PERSONA_FOLDER_MAP.get(persona_key)
    stories = STORY_ORDER_MAP.get(persona_key, [])
    story_num = stories.index(story_key) + 1
    minio_prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"

    # Собираем все картинки из локальной папки
    exts = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
    local_files = []
    for ext in exts:
        local_files.extend(glob.glob(os.path.join(local_dir, ext)))
    local_files = sorted(local_files)

    if not local_files:
        print(f"  ⚠️  В папке {local_dir} нет картинок (.jpg/.jpeg/.png)")
        return 0

    # Определяем стартовый индекс (продолжаем с конца)
    existing_count = count_files_in_path(client, minio_prefix)
    start_index = existing_count + 1

    print(f"  Найдено файлов локально: {len(local_files)}")
    print(f"  Уже в MinIO: {existing_count} шт, загружаем начиная с {start_index:03d}.png")

    uploaded = 0
    for local_path in local_files:
        filename = f"{start_index:03d}.png"
        object_name = f"{minio_prefix}{filename}"
        ext = os.path.splitext(local_path)[1].lower()
        content_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"

        try:
            client.fput_object(
                MINIO_BUCKET,
                object_name,
                local_path,
                content_type=content_type,
            )
            print(f"  ✅ {os.path.basename(local_path)} → {object_name}")
            start_index += 1
            uploaded += 1
        except S3Error as e:
            print(f"  ❌ Ошибка загрузки {local_path}: {e}")

    return uploaded


# ==================== SEX_IMAGE_POOL UPDATE ====================

def update_sex_images_py(pool: dict):
    """Обновляет константу SEX_IMAGE_POOL в sex_images.py."""
    if not os.path.exists(SEX_IMAGES_PY):
        print(f"❌ Файл не найден: {SEX_IMAGES_PY}")
        return False

    with open(SEX_IMAGES_PY, "r", encoding="utf-8") as f:
        content = f.read()

    # Генерируем новый блок SEX_IMAGE_POOL
    lines = ["SEX_IMAGE_POOL = {\n"]
    # Сортируем по алфавиту для читаемости
    for persona_key in sorted(pool.keys()):
        persona_data = pool[persona_key]
        lines.append(f'    "{persona_key}": {{\n')
        for story_key in STORY_ORDER_MAP.get(persona_key, []):
            if story_key not in persona_data:
                continue
            story_data = persona_data[story_key]
            # Сортируем сцены по номеру
            sorted_scenes = dict(sorted(story_data.items(), key=lambda x: int(x[0].split("_")[1])))
            scene_str = ", ".join(f'"{k}": {v}' for k, v in sorted_scenes.items())
            lines.append(f'        "{story_key}": {{{scene_str}}},\n')
        lines.append("    },\n")
    lines.append("    # taya: no sex images yet\n")
    lines.append("}\n")

    new_pool_block = "".join(lines)

    # Заменяем блок SEX_IMAGE_POOL в файле
    pattern = r"SEX_IMAGE_POOL\s*=\s*\{.*?^(?=\s*#\s*MinIO base path|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if not match:
        print("❌ Не нашёл блок SEX_IMAGE_POOL в файле — обновление не выполнено")
        return False

    new_content = content[:match.start()] + new_pool_block + "\n" + content[match.end():]

    # Бэкап
    backup_path = SEX_IMAGES_PY + ".bak"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)

    with open(SEX_IMAGES_PY, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ sex_images.py обновлён (бэкап: {backup_path})")
    return True


# ==================== DISPLAY ====================

def print_pool_status(client: Minio):
    """Выводит таблицу текущего состояния пула."""
    print("\n" + "=" * 70)
    print("📊 ТЕКУЩЕЕ СОСТОЯНИЕ ПУЛА")
    print("=" * 70)

    total_photos = 0
    for persona_key in sorted(PERSONA_FOLDER_MAP.keys()):
        if persona_key == "taya":
            continue
        folder = PERSONA_FOLDER_MAP[persona_key]
        stories = STORY_ORDER_MAP.get(persona_key, [])
        persona_total = 0

        print(f"\n👤 {persona_key.upper()} ({folder})")
        for i, story_key in enumerate(stories):
            story_num = i + 1
            story_total = 0
            scene_info = []
            for schene_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                schene_key = f"schene_{schene_num}"
                prefix = f"{SEX_PREFIX}/{folder}/story_{story_num}/{schene_key}/"
                cnt = count_files_in_path(client, prefix)
                if cnt > 0:
                    scene_info.append(f"{schene_key}:{cnt}")
                    story_total += cnt
            status = "  ".join(scene_info) if scene_info else "— пусто"
            print(f"  story_{story_num} ({story_key}): {status}  [{story_total} фото]")
            persona_total += story_total

        print(f"  Итого {persona_key}: {persona_total} фото")
        total_photos += persona_total

    print(f"\n{'=' * 70}")
    print(f"📸 ВСЕГО ФОТО В ПУЛЕ: {total_photos}")
    print("=" * 70 + "\n")


def choose_from_list(title: str, items: list) -> str | None:
    """Интерактивный выбор из списка."""
    print(f"\n{title}")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    print("  0. Отмена")
    while True:
        try:
            choice = input("Выбор: ").strip()
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            print("Неверный номер")
        except (ValueError, EOFError):
            return None


# ==================== MAIN MENU ====================

def menu_upload(client: Minio):
    """Загрузка новых фоток."""
    # Выбор персонажа
    personas = [p for p in sorted(PERSONA_FOLDER_MAP.keys()) if p != "taya"]
    persona_key = choose_from_list("Выбери персонажа:", personas)
    if not persona_key:
        return

    # Выбор истории
    stories = STORY_ORDER_MAP.get(persona_key, [])
    story_key = choose_from_list(f"Выбери историю для {persona_key}:", stories)
    if not story_key:
        return

    # Выбор позы
    pose_names = list(SCENE_MAP.keys())
    pose_display = [SCENE_NAMES_RU[p] for p in pose_names]
    chosen_display = choose_from_list("Выбери позу:", pose_display)
    if not chosen_display:
        return
    scene_name = pose_names[pose_display.index(chosen_display)]
    schene_key = f"schene_{SCENE_MAP[scene_name]}"

    # Текущее состояние
    existing = get_existing_file_count(client, persona_key, story_key, schene_key)
    print(f"\n📁 {persona_key} / {story_key} / {schene_key}")
    print(f"   Сейчас в MinIO: {existing} фото")

    # Путь к локальной папке
    local_dir = input("\nПуть к папке с новыми фотками: ").strip()
    if not local_dir or not os.path.isdir(local_dir):
        print(f"❌ Папка не найдена: {local_dir}")
        return

    # Загрузка
    print(f"\n⬆️  Загружаю в {SEX_PREFIX}/{PERSONA_FOLDER_MAP[persona_key]}/story_X/{schene_key}/...")
    uploaded = upload_images(client, local_dir, persona_key, story_key, schene_key)

    if uploaded > 0:
        print(f"\n✅ Загружено {uploaded} фото")
        update = input("\nОбновить SEX_IMAGE_POOL в sex_images.py? (y/n): ").strip().lower()
        if update == "y":
            print("\n🔄 Сканирую MinIO...")
            pool = scan_all_pool(client)
            update_sex_images_py(pool)


def menu_status(client: Minio):
    """Показать статус пула."""
    print("\n🔄 Сканирую MinIO...")
    print_pool_status(client)


def menu_rescan(client: Minio):
    """Пересканировать MinIO и обновить sex_images.py."""
    print("\n🔄 Сканирую MinIO...")
    pool = scan_all_pool(client)

    print("\n📊 Результат сканирования:")
    total = 0
    for persona_key, stories in sorted(pool.items()):
        persona_total = sum(sum(s.values()) for s in stories.values())
        total += persona_total
        print(f"  {persona_key}: {len(stories)} историй, {persona_total} фото")
    print(f"  Итого: {total} фото")

    confirm = input("\nОбновить SEX_IMAGE_POOL в sex_images.py? (y/n): ").strip().lower()
    if confirm == "y":
        update_sex_images_py(pool)


def main():
    print("=" * 50)
    print("🎬 Sex Image Pool Manager")
    print("=" * 50)

    try:
        client = get_client()
        # Проверяем подключение
        client.bucket_exists(MINIO_BUCKET)
        print(f"✅ Подключено к MinIO ({MINIO_ENDPOINT})")
    except Exception as e:
        print(f"❌ Не удалось подключиться к MinIO: {e}")
        print("   Убедись что скрипт запущен на сервере внутри Docker-сети или с проброшенным портом")
        sys.exit(1)

    while True:
        print("\n📋 МЕНЮ:")
        print("  1. Показать статус пула (сколько фото по каждой позе)")
        print("  2. Загрузить новые фотки")
        print("  3. Пересканировать MinIO и обновить sex_images.py")
        print("  0. Выход")

        choice = input("\nВыбор: ").strip()

        if choice == "1":
            menu_status(client)
        elif choice == "2":
            menu_upload(client)
        elif choice == "3":
            menu_rescan(client)
        elif choice == "0":
            print("Выход.")
            break
        else:
            print("Неверный выбор")


if __name__ == "__main__":
    main()
