"""
Sex images pool for chat.

Pre-generated sex scene images stored in MinIO.
Images are sent based on LLM-detected pose from user messages.
Each scene maintains its own cyclic index per dialog.
"""

from typing import Optional

# Mapping: persona_key -> MinIO folder name
# Some persona folders differ from persona_key
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

# Mapping: persona_key -> ordered list of story_keys (matches webapp order)
STORY_ORDER_MAP = {
    "lina": ["sauna_support", "shower_flirt", "gym_late", "competition_prep"],
    "mei": ["mall_bench", "car_ride", "home_visit", "regular_visits"],
    "julie": ["home_tutor", "teacher_punishment", "bus_fun"],
    "hani": ["photoshoot", "pool", "elevator"],
    "pai": ["dinner", "window", "car"],
    "ash": ["living_room", "bedroom"],
    "anastasia": ["classroom", "bathroom"],
    "sasha": ["auction", "plane", "party"],
    "yuna": ["first_evening", "city_lights", "tea_secrets"],
    "roxy": ["hitchhiker", "maid", "beach"],
    "taya": ["bar_back_exit", "gaming_center", "friends_wife", "office_elevator"],
    "marianna": ["support", "cozy", "flirt", "serious"],
    "stacey": ["rooftop_sunset", "hints_game", "night_park", "confession"],
}

# Mapping: pose_name -> schene number in MinIO
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

# Mapping: persona_key -> story_key -> schene_N -> file count
# Auto-generated from MinIO contents
SEX_IMAGE_POOL = {
    "anastasia": {
        "classroom": {"schene_1": 11, "schene_2": 9, "schene_3": 9, "schene_4": 10, "schene_5": 9, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 6},
        "bathroom": {"schene_1": 10, "schene_2": 10, "schene_3": 10, "schene_4": 11, "schene_5": 9, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 11},
    },
    "ash": {
        "living_room": {"schene_1": 10, "schene_2": 10, "schene_3": 11, "schene_4": 10, "schene_5": 10, "schene_6": 9, "schene_8": 10, "schene_9": 9, "schene_10": 10},
        "bedroom": {"schene_1": 10, "schene_2": 10, "schene_3": 10, "schene_4": 9, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 9},
    },
    "hani": {
        "photoshoot": {"schene_1": 11, "schene_2": 10, "schene_3": 10, "schene_4": 11, "schene_5": 9, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 10},
        "pool": {"schene_1": 11, "schene_2": 9, "schene_3": 9, "schene_4": 9, "schene_5": 8, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 10},
        "elevator": {"schene_1": 12, "schene_2": 10, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 9},
    },
    "julie": {
        "home_tutor": {"schene_1": 11, "schene_2": 10, "schene_3": 12, "schene_4": 12, "schene_5": 10, "schene_6": 11, "schene_8": 10, "schene_9": 11, "schene_10": 10},
        "teacher_punishment": {"schene_1": 11, "schene_2": 11, "schene_3": 10, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 11, "schene_9": 11, "schene_10": 12},
        "bus_fun": {"schene_1": 10, "schene_2": 10, "schene_3": 12, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 10, "schene_9": 11, "schene_10": 9},
    },
    "lina": {
        "sauna_support": {"schene_1": 9, "schene_2": 11, "schene_3": 12, "schene_4": 12, "schene_5": 8, "schene_6": 14, "schene_7": 11, "schene_8": 7, "schene_9": 9, "schene_10": 10},
        "shower_flirt": {"schene_1": 10, "schene_2": 10, "schene_3": 9, "schene_4": 11, "schene_5": 10, "schene_6": 11, "schene_8": 11, "schene_9": 8, "schene_10": 11},
        "gym_late": {"schene_1": 10, "schene_2": 11, "schene_3": 10, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 10, "schene_9": 9, "schene_10": 10},
        "competition_prep": {"schene_1": 10, "schene_2": 7, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_7": 10},
    },
    "marianna": {
        "support": {"schene_1": 10, "schene_2": 11, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 10},
        "cozy": {"schene_1": 10, "schene_2": 10, "schene_3": 10, "schene_4": 9, "schene_5": 11, "schene_6": 11, "schene_8": 9, "schene_9": 10, "schene_10": 10},
        "flirt": {"schene_1": 10, "schene_2": 10, "schene_3": 12, "schene_4": 11, "schene_5": 11, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 10},
        "serious": {"schene_1": 10, "schene_2": 11, "schene_3": 10, "schene_4": 11, "schene_5": 10, "schene_6": 9, "schene_8": 10, "schene_9": 10, "schene_10": 10},
    },
    "mei": {
        "mall_bench": {"schene_1": 12, "schene_2": 14, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 11, "schene_9": 10, "schene_10": 10},
        "car_ride": {"schene_1": 11, "schene_2": 10, "schene_3": 10, "schene_4": 10, "schene_5": 11, "schene_6": 11, "schene_8": 10, "schene_9": 11, "schene_10": 8},
        "home_visit": {"schene_1": 11, "schene_2": 10, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 9, "schene_9": 10, "schene_10": 8},
        "regular_visits": {"schene_1": 10, "schene_2": 11, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 11, "schene_8": 10, "schene_9": 11, "schene_10": 12},
    },
    "pai": {
        "dinner": {"schene_1": 10, "schene_2": 10, "schene_3": 10, "schene_4": 11, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 12, "schene_10": 10},
        "window": {"schene_1": 10, "schene_2": 10, "schene_3": 12, "schene_4": 11, "schene_5": 14, "schene_6": 11, "schene_8": 11, "schene_9": 11, "schene_10": 11},
        "car": {"schene_1": 11, "schene_2": 10, "schene_3": 12, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 10},
    },
    "roxy": {
        "hitchhiker": {"schene_1": 11, "schene_2": 11, "schene_3": 11, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 11, "schene_9": 10, "schene_10": 3},
        "maid": {"schene_1": 10, "schene_2": 10, "schene_3": 11, "schene_4": 10, "schene_5": 11, "schene_6": 11, "schene_8": 10, "schene_9": 10, "schene_10": 11},
        "beach": {"schene_1": 10, "schene_2": 10, "schene_3": 10, "schene_4": 10, "schene_5": 11, "schene_6": 10, "schene_8": 12, "schene_9": 10, "schene_10": 9},
    },
    "sasha": {
        "auction": {"schene_1": 17, "schene_2": 9, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 9, "schene_8": 12, "schene_9": 11, "schene_10": 11},
        "plane": {"schene_1": 12, "schene_2": 10, "schene_3": 11, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 10, "schene_10": 6},
        "party": {"schene_1": 11, "schene_2": 10, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 22, "schene_9": 21, "schene_10": 11},
    },
    "stacey": {
        "rooftop_sunset": {"schene_1": 10, "schene_2": 12, "schene_3": 12, "schene_4": 10, "schene_5": 10, "schene_6": 9, "schene_8": 9, "schene_9": 9, "schene_10": 10},
        "hints_game": {"schene_1": 10, "schene_2": 11, "schene_3": 11, "schene_4": 11, "schene_5": 10, "schene_6": 10, "schene_8": 11, "schene_9": 11, "schene_10": 6},
        "night_park": {"schene_1": 10, "schene_2": 10, "schene_3": 12, "schene_4": 10, "schene_5": 12, "schene_6": 11, "schene_8": 10, "schene_9": 11, "schene_10": 11},
        "confession": {"schene_1": 10, "schene_2": 11, "schene_3": 10, "schene_4": 10, "schene_5": 10, "schene_6": 10, "schene_8": 10, "schene_9": 9, "schene_10": 8},
    },
    "yuna": {
        "first_evening": {"schene_1": 10, "schene_2": 12, "schene_3": 11, "schene_4": 9, "schene_5": 11, "schene_6": 10, "schene_8": 11, "schene_9": 12, "schene_10": 11},
        "city_lights": {"schene_1": 10, "schene_2": 12, "schene_3": 10, "schene_4": 11, "schene_5": 10, "schene_6": 10, "schene_9": 9, "schene_10": 9},
    },
    # taya: no sex images yet
}

# MinIO base path for sex images
SEX_IMAGES_MINIO_PREFIX = "sex-pics"


def has_sex_images(persona_key: str) -> bool:
    """Check if persona has sex images in the pool."""
    return persona_key in SEX_IMAGE_POOL


def _get_story_number(persona_key: str, story_key: str) -> Optional[int]:
    """Get 1-based story number from story_key."""
    stories = STORY_ORDER_MAP.get(persona_key)
    if not stories:
        return None
    try:
        return stories.index(story_key) + 1
    except ValueError:
        return None


def get_sex_image_url(
    persona_key: str,
    story_key: str,
    scene_name: str,
    index: int,
) -> Optional[str]:
    """
    Get internal MinIO URL for sex image.

    Args:
        persona_key: Persona key (e.g. 'lina')
        story_key: Story key (e.g. 'sauna_support')
        scene_name: Pose name (e.g. 'doggy')
        index: Current image index (0-based), will be wrapped cyclically

    Returns:
        Internal MinIO URL or None if not available
    """
    # Check persona has images
    persona_pool = SEX_IMAGE_POOL.get(persona_key)
    if not persona_pool:
        return None

    # Check story exists
    story_pool = persona_pool.get(story_key)
    if not story_pool:
        return None

    # Map scene name to schene number
    schene_num = SCENE_MAP.get(scene_name)
    if schene_num is None:
        return None

    schene_key = f"schene_{schene_num}"

    # Check scene exists and has images
    image_count = story_pool.get(schene_key)
    if not image_count:
        return None

    # Get folder name and story number
    folder_name = PERSONA_FOLDER_MAP.get(persona_key)
    if not folder_name:
        return None

    story_number = _get_story_number(persona_key, story_key)
    if not story_number:
        return None

    # Cyclic index
    img_index = index % image_count

    # Files renamed to sequential: 001.png, 002.png, etc.
    filename = f"{img_index + 1:03d}.png"

    path = f"{SEX_IMAGES_MINIO_PREFIX}/{folder_name}/story_{story_number}/{schene_key}/{filename}"
    return f"http://minio:9000/vitte-bot/{path}"


def should_send_sex_image(message_count: int) -> bool:
    """
    Check if sex image should be sent based on message count.

    First drop at 9th assistant message (message_count=17).
    Then every 3rd assistant message (12th=mc23, 15th=mc29, 18th=mc35...).

    Args:
        message_count: Predicted message_count after this exchange (dialog.message_count + 2)

    Returns:
        True if it's time to potentially send a sex image
    """
    # assistant_count = (message_count + 1) // 2
    # greeting=1 msg, then each exchange adds 2 (user+assistant)
    # message_count=1 → assistant_count=1 (greeting)
    # message_count=3 → assistant_count=2
    # message_count=17 → assistant_count=9
    assistant_count = (message_count + 1) // 2

    if assistant_count < 9:
        return False

    # First drop at 9, then every 3 (12, 15, 18, 21...)
    return (assistant_count - 9) % 3 == 0
