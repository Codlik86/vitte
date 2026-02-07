#!/usr/bin/env python3
"""
Upload cropped persona images to MinIO
Maps file names to persona keys
"""

from pathlib import Path
from minio import Minio
from minio.error import S3Error
import os

# MinIO configuration
MINIO_ENDPOINT = "195.209.210.96:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "MIn!o_pASS_vitte2006_&&_pic$")
BUCKET_NAME = "vitte-bot"
UPLOAD_FOLDER = "persona-dialogs"

# File name to persona_key mapping
FILE_TO_PERSONA = {
    # Stacey (4 files - use first one as default)
    "Stacey - Вечер на крыше и закат вдвоём.jpg": "stacey",

    # Mei (4 files)
    "Mei - Встреча в торговом центре.png": "mei",

    # Yuna (3 files)
    "Yuna - Первый вечер и мягкая беседа.jpg": "yuna",

    # Taya (4 files)
    "Taya - Служебный выход бара.png": "taya",

    # Julie (3 files)
    "Julie - Репетитор на дому.png": "julie",

    # Ash (2 files)
    "Ash - В гостиной.png": "ash",

    # Lina (4 files)
    "Lina - Прятки в сауне.png": "lina",

    # Marianna (4 files)
    "Marianna - Ночное эхо.png": "marianna",
}

def upload_images():
    """Upload cropped images to MinIO"""

    # Initialize MinIO client
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    print(f"📡 Connected to MinIO at {MINIO_ENDPOINT}")
    print(f"📦 Bucket: {BUCKET_NAME}")
    print(f"📁 Folder: {UPLOAD_FOLDER}\n")

    # Check if bucket exists
    if not client.bucket_exists(BUCKET_NAME):
        print(f"❌ Bucket '{BUCKET_NAME}' does not exist!")
        return

    cropped_dir = Path(__file__).parent / "cropped_736x414"

    if not cropped_dir.exists():
        print(f"❌ Directory not found: {cropped_dir}")
        return

    uploaded_count = 0

    for filename, persona_key in FILE_TO_PERSONA.items():
        file_path = cropped_dir / filename

        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue

        # Determine file extension
        ext = file_path.suffix  # .jpg or .png

        # Object name in MinIO: persona-dialogs/stacey.jpg
        object_name = f"{UPLOAD_FOLDER}/{persona_key}{ext}"

        try:
            # Upload file
            client.fput_object(
                BUCKET_NAME,
                object_name,
                str(file_path),
                content_type=f"image/{ext[1:]}"  # image/jpg or image/png
            )

            print(f"✅ Uploaded: {persona_key}{ext} ({filename})")
            uploaded_count += 1

        except S3Error as e:
            print(f"❌ Error uploading {filename}: {e}")

    print(f"\n🎉 Done! Uploaded {uploaded_count}/{len(FILE_TO_PERSONA)} images")
    print(f"\nImages accessible at:")
    print(f"  Internal: http://minio:9000/{BUCKET_NAME}/{UPLOAD_FOLDER}/{{persona_key}}.jpg")
    print(f"  Public:   https://craveme.tech/storage/{UPLOAD_FOLDER}/{{persona_key}}.jpg")


if __name__ == "__main__":
    upload_images()
