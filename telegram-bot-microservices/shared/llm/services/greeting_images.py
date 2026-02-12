"""
Greeting images pool for chat start.

Each persona+story has a set of pre-generated images stored in MinIO.
Images are sent cyclically on each dialog greeting.
"""

from typing import Optional

# Mapping: persona_key -> {story_key: image_count}
# story_key order matches stories.py dict order (story1, story2, ...)
GREETING_IMAGE_POOL = {
    "lina": {
        "sauna_support": 16,
        "shower_flirt": 15,
        "gym_late": 14,
        "competition_prep": 18,
    },
    "marianna": {
        "support": 18,
        "cozy": 16,
        "flirt": 22,
        "serious": 20,
    },
    "mei": {
        "mall_bench": 18,
        "car_ride": 16,
        "home_visit": 18,
        "regular_visits": 17,
    },
    "taya": {
        "bar_back_exit": 18,
        "gaming_center": 21,
        "friends_wife": 20,
        "office_elevator": 15,
    },
    "julie": {
        "home_tutor": 22,
        "teacher_punishment": 17,
        "bus_fun": 17,
    },
    "ash": {
        "living_room": 14,
        "bedroom": 17,
    },
    "anastasia": {
        "classroom": 18,
        "bathroom": 18,
    },
    "sasha": {
        "auction": 21,
        "plane": 17,
        "party": 19,
    },
    "roxy": {
        "hitchhiker": 22,
        "maid": 17,
        "beach": 13,
    },
    "pai": {
        "dinner": 17,
        "window": 18,
        "car": 18,
    },
    "hani": {
        "photoshoot": 16,
        "pool": 17,
        "elevator": 14,
    },
    "stacey": {
        "rooftop_sunset": 16,
        "hints_game": 15,
        "confession": 20,
        "night_park": 15,
    },
}

# MinIO base path for greeting images
GREETING_IMAGES_MINIO_PREFIX = "chat-start-pics"


def get_greeting_image_path(
    persona_key: str,
    story_key: str,
    index: int,
) -> Optional[str]:
    """
    Get MinIO path for greeting image by index (cyclic).

    Args:
        persona_key: Persona key (e.g. 'lina')
        story_key: Story key (e.g. 'sauna_support')
        index: Current greeting index (0-based), will be wrapped cyclically

    Returns:
        MinIO object path like 'chat-start-pics/lina/sauna_support/001.png'
        or None if persona/story not found
    """
    persona_pool = GREETING_IMAGE_POOL.get(persona_key)
    if not persona_pool:
        return None

    image_count = persona_pool.get(story_key)
    if not image_count:
        return None

    # Cyclic index
    img_index = index % image_count
    # 1-based, zero-padded filename
    filename = f"{img_index + 1:03d}.png"

    return f"{GREETING_IMAGES_MINIO_PREFIX}/{persona_key}/{story_key}/{filename}"


def get_greeting_image_url(
    persona_key: str,
    story_key: str,
    index: int,
) -> Optional[str]:
    """
    Get internal MinIO URL for greeting image.

    Returns URL like 'http://minio:9000/vitte-bot/chat-start-pics/lina/sauna_support/001.png'
    """
    path = get_greeting_image_path(persona_key, story_key, index)
    if not path:
        return None
    return f"http://minio:9000/vitte-bot/{path}"
