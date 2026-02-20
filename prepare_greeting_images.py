#!/usr/bin/env python3
"""
Prepare greeting images for MinIO upload.
Renames files to sequential 001.png, 002.png format
and organizes by persona_key/story_key.
"""
import os
import shutil

SRC = "/Users/dmitriianisimov/Desktop/vitte_dev_for_deploy/new-pics-chat-start"
DST = "/Users/dmitriianisimov/Desktop/vitte_dev_for_deploy/chat-start-pics-prepared"

# Mapping: folder name -> persona_key, story_number -> story_key
STORY_MAP = {
    "lina": ["sauna_support", "shower_flirt", "gym_late", "competition_prep"],
    "marianna": ["support", "cozy", "flirt", "serious"],
    "mei": ["mall_bench", "car_ride", "home_visit", "regular_visits"],
    "taya": ["bar_back_exit", "gaming_center", "friends_wife", "office_elevator"],
    "julie": ["home_tutor", "teacher_punishment", "bus_fun"],
    "ash": ["living_room", "bedroom"],
    "anastasia": ["classroom", "bathroom"],
    "sasha": ["auction", "plane", "party"],
    "roxy": ["hitchhiker", "maid", "beach"],
    "pai": ["dinner", "window", "car"],
    "hani": ["photoshoot", "pool", "elevator"],
    "stasy": ["rooftop_sunset", "hints_game", "confession", "night_park"],  # folder is "stasy" but persona key is "stacey"
}

# Folder name -> actual persona key in DB
FOLDER_TO_KEY = {
    "stasy": "stacey",
}

os.makedirs(DST, exist_ok=True)

for folder_name, story_keys in STORY_MAP.items():
    persona_key = FOLDER_TO_KEY.get(folder_name, folder_name)

    for story_idx, story_key in enumerate(story_keys, 1):
        story_dir = os.path.join(SRC, folder_name, f"story{story_idx}")
        if not os.path.isdir(story_dir):
            print(f"SKIP: {story_dir} not found")
            continue

        dst_dir = os.path.join(DST, persona_key, story_key)
        os.makedirs(dst_dir, exist_ok=True)

        # Get sorted PNG files
        pngs = sorted([f for f in os.listdir(story_dir) if f.endswith('.png')])

        for i, png_file in enumerate(pngs, 1):
            src_path = os.path.join(story_dir, png_file)
            dst_path = os.path.join(dst_dir, f"{i:03d}.png")
            shutil.copy2(src_path, dst_path)

        print(f"{persona_key}/{story_key}: {len(pngs)} files")

print("\nDone! Files prepared in:", DST)
