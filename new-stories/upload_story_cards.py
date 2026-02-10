#!/usr/bin/env python3
"""
Upload cropped story card images to MinIO (story-dialogs/ folder)
Same approach as old personas — flat structure, no subfolders.
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
UPLOAD_FOLDER = "story-dialogs"

# Source cropped file -> target name in MinIO
FILE_MAP = {
    "sasha-story-auction.jpeg": "sasha-story-auction.jpeg",
    "sasha-story-plane.jpeg": "sasha-story-plane.jpeg",
    "sasha-story-party.jpeg": "sasha-story-party.jpeg",
    "anastasia-story-classroom.jpeg": "anastasia-story-classroom.jpeg",
    "anastasia-story-bathroom.jpeg": "anastasia-story-bathroom.jpeg",
    "roxy-story-hitchhiker.jpeg": "roxy-story-hitchhiker.jpeg",
    "roxy-story-maid.jpeg": "roxy-story-maid.jpeg",
    "roxy-story-beach.jpeg": "roxy-story-beach.jpeg",
    "pai-story-dinner.jpeg": "pai-story-dinner.jpeg",
    "pai-story-window.jpeg": "pai-story-window.jpeg",
    "pai-story-car.jpeg": "pai-story-car.jpeg",
    "hani-story-photoshoot.jpeg": "hani-story-photoshoot.jpeg",
    "hani-story-pool.jpeg": "hani-story-pool.jpeg",
    "hani-story-elevator.jpeg": "hani-story-elevator.jpeg",
}


def upload_images():
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    print(f"Connected to MinIO at {MINIO_ENDPOINT}")

    if not client.bucket_exists(BUCKET_NAME):
        print(f"Bucket '{BUCKET_NAME}' does not exist!")
        return

    src_dir = Path(__file__).parent / "upload_ready"

    uploaded = 0
    for src_name, dst_name in FILE_MAP.items():
        file_path = src_dir / src_name
        if not file_path.exists():
            print(f"MISSING: {src_name}")
            continue

        object_name = f"{UPLOAD_FOLDER}/{dst_name}"
        try:
            client.fput_object(
                BUCKET_NAME,
                object_name,
                str(file_path),
                content_type="image/jpeg"
            )
            print(f"OK: {object_name}")
            uploaded += 1
        except S3Error as e:
            print(f"ERROR {src_name}: {e}")

    print(f"\nDone! Uploaded {uploaded}/{len(FILE_MAP)}")


if __name__ == "__main__":
    upload_images()
