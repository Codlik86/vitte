#!/usr/bin/env python3
"""
Upload prepared greeting images to MinIO.
Run on server: python3 /tmp/upload_to_minio.py
"""
import os
import subprocess

MINIO_ALIAS = "local"
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_USER = "minioadmin"
MINIO_PASS = 'MIn!o_pASS_vitte2006_&&_pic$'
BUCKET = "vitte-bot"
SRC_DIR = "/tmp/chat-start-pics-prepared"
DST_PREFIX = "chat-start-pics"

# First, configure mc alias
subprocess.run([
    "mc", "alias", "set", MINIO_ALIAS,
    MINIO_ENDPOINT, MINIO_USER, MINIO_PASS
], check=True)

# Upload recursively
for persona in sorted(os.listdir(SRC_DIR)):
    persona_path = os.path.join(SRC_DIR, persona)
    if not os.path.isdir(persona_path):
        continue
    for story in sorted(os.listdir(persona_path)):
        story_path = os.path.join(persona_path, story)
        if not os.path.isdir(story_path):
            continue

        dest = f"{MINIO_ALIAS}/{BUCKET}/{DST_PREFIX}/{persona}/{story}/"
        pngs = [f for f in os.listdir(story_path) if f.endswith('.png')]
        print(f"Uploading {len(pngs)} files to {DST_PREFIX}/{persona}/{story}/")

        subprocess.run([
            "mc", "cp", "--recursive",
            story_path + "/",
            dest,
        ], check=True)

print("\nDone! All greeting images uploaded to MinIO.")
