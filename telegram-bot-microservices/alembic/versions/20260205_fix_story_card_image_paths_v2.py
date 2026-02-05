"""Fix story_cards image paths to match actual files on disk

Revision ID: 020
Revises: 019
Create Date: 2026-02-05

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None

# Маппинг: story_id -> реальный путь файла на диске
CORRECT_IMAGES = {
    "lina": {
        "sauna_support": "personas/lina-story-support.png",
        "shower_flirt": "personas/lina-story-flirt.png",
        "gym_late": "personas/lina-story-cozy.png",
        "competition_prep": "personas/lina-story-serious.png",
    },
    "marianna": {
        "balcony_night": "personas/marianna-story-serious.png",
        "wine_evening": "personas/marianna-story-flirt.png",
        "elevator_stuck": "personas/marianna-story-support.png",
    },
    "mei": {
        "mall_bench": "personas/mei-story-mall.png",
        "car_ride": "personas/mei-story-car.png",
        "home_visit": "personas/mei-story-home.png",
        "regular_visits": "personas/mei-story-hook.png",
    },
    "stacey": {
        "rooftop_sunset": "personas/stacey-story-date.jpg",
        "hints_game": "personas/stacey-story-tease.jpg",
        "confession": "personas/stacey-story-confession.jpg",
        "night_park": "personas/stacey-story-adventure.jpg",
    },
    "yuna": {
        "first_evening": "personas/yuna-story-hello.jpg",
        "city_lights": "personas/yuna-story-citywalk.jpg",
        "tea_secrets": "personas/yuna-story-teahouse.jpg",
    },
    "taya": {
        "bar_back_exit": "personas/taya-story-bar.png",
        "gaming_center": "personas/taya-story-gaming.png",
        "friends_wife": "personas/taya-story-friend.png",
        "office_elevator": "personas/taya-story-office.png",
    },
    "julie": {
        "home_tutor": "personas/julie-story-tutor.png",
        "teacher_punishment": "personas/julie-story-punish.png",
        "bus_fun": "personas/julie-story-bus.png",
    },
    "ash": {
        "living_room": "personas/ash-story-livingroom.png",
        "bedroom": "personas/ash-story-bedroom.png",
    },
}


def upgrade() -> None:
    conn = op.get_bind()

    for persona_key, image_map in CORRECT_IMAGES.items():
        row = conn.execute(
            sa.text("SELECT story_cards FROM personas WHERE key = :key"),
            {"key": persona_key}
        ).fetchone()

        if not row or not row[0]:
            continue

        story_cards = row[0] if isinstance(row[0], list) else json.loads(row[0])

        for card in story_cards:
            card_id = card.get("id") or card.get("key")
            if card_id in image_map:
                card["image"] = image_map[card_id]

        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = :key"),
            {"cards": json.dumps(story_cards, ensure_ascii=False), "key": persona_key}
        )


def downgrade() -> None:
    pass
